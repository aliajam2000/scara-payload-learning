"""Post-review instrumentation. Original model/experiment files remain unchanged."""
import csv,json,time,hashlib,platform,importlib.metadata,argparse
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from . import model_r1 as m
from .experiment import scenario,PRIOR,PRIOR_VAR,batch as original_batch

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=dict(noise=1.,inflation=16.,margin_scale=1.,probe_T=.4,allowance=.9,fs=1.,structure=0,physical_payload=False)
METHODS=['passive','always_probe','batch_aware','ignore_passive','uncertainty_trigger','oracle']

def batch(seed,N,family,method,settings):
    c={**DEFAULT,**settings};dt=.002
    actual,q0,q1=scenario(seed,family)
    if c['physical_payload']:
        rg=np.random.default_rng(seed+700000).uniform(.06,.14)
        actual[1]=actual[0]*rg**2
    theta=actual.copy() if method=='oracle' else PRIOR.copy()
    P=np.full(2,1e-20) if method=='oracle' else PRIOR_VAR.copy()
    x=np.r_[q0,np.zeros(4)];learn=method!='oracle';failed=False;completed=0
    times=dict(grasp=0.,probe=0.,loaded=0.,release=0.,returning=0.)
    maxa=0.;maxv=0.;probe_a=0.;probe_v=0.;planning=0.;probes=0;reached=0
    gain=float('nan');history=[];cap_count=0;rounding=[];pads=[];probe_prediction=[]
    fixed_mean=None;openP=None

    def execute(a,b,T,loaded,stream,kind):
        nonlocal x,theta,P,failed,maxa,maxv,probe_a,probe_v
        est=theta if loaded else np.zeros(2);var=P if loaded else np.full(2,1e-20)
        out=m.segment(x,a,b,T,est,var,learn and loaded,actual if loaded else np.zeros(2),
            dt,seed*10000+stream,c['fs'],c['noise'],1,c['inflation'],c['structure'])
        x=out[0]
        if loaded:theta,P=out[1],out[2]
        times[kind]+=out[3];failed=failed or not out[4]
        maxv=max(maxv,out[8]);maxa=max(maxa,out[9])
        if kind=='probe':probe_v=max(probe_v,out[8]);probe_a=max(probe_a,out[9])
        return out[3]

    for item in range(N):
        execute(q0,q0,.05,True,item*10+1,'grasp')
        if failed:break
        if item==0:
            reached=1;fixed_mean=theta.copy();openP=P.copy()
            tic=time.perf_counter();take=False
            if method=='always_probe':take=True
            elif method=='uncertainty_trigger':take=np.sqrt(P[1])/(.008+theta[1])>.2
            elif method in ('batch_aware','ignore_passive'):
                take,gain=m.probe_decision(N,theta,P,q0,q1,dt,method=='ignore_passive',c['noise'],c['inflation'],c['margin_scale'],c['probe_T'],c['allowance'])
            planning+=time.perf_counter()-tic
            if take:
                probes=1;qp=q0.copy();qp[3]+=.6
                pred=m.forecast(P,theta,q0,qp,c['probe_T'],dt,c['noise'],c['inflation'])
                pred=m.forecast(pred,theta,qp,q0,c['probe_T'],dt,c['noise'],c['inflation'])
                execute(q0,qp,c['probe_T'],True,9001,'probe')
                if not failed:execute(qp,q0,c['probe_T'],True,9002,'probe')
                probe_prediction=[*np.sqrt(pred),*np.sqrt(P)]
                openP=pred
                if failed:break
        tic=time.perf_counter()
        T=float(m.schedule(q0,q1,theta,P,True,c['margin_scale']))
        planning+=time.perf_counter()-tic
        sd=np.sqrt(P);pad=c['margin_scale']*(.16*sd[0]+.16*np.sqrt(sd[1]/(.008+theta[1])))
        pads.append(pad);cap_count+=int(np.any(theta+2*sd>np.array([2.,.03])))
        no_pad=float(m.schedule(q0,q1,theta,P,True,0.))
        # Candidate base is already on the 25 ms grid; residual quantization
        # may include one floating point grid boundary, preserved from v1.
        rounding.append(T-no_pad-pad)
        pred=m.forecast(P,theta,q0,q1,T,dt,c['noise'],c['inflation'])
        predT=float(m.schedule(q0,q1,fixed_mean,openP,True,c['margin_scale']))
        openP=m.forecast(openP,fixed_mean,q0,q1,predT,dt,c['noise'],c['inflation'])
        elapsed=execute(q0,q1,T,True,item*10+2,'loaded')
        history.append(dict(item=item+1,T=T,elapsed=elapsed,mass=theta[0],inertia=theta[1],
            sd_mass=np.sqrt(P[0]),sd_inertia=np.sqrt(P[1]),pred_sd_mass=np.sqrt(pred[0]),pred_sd_inertia=np.sqrt(pred[1]),
            rollout_sd_mass=np.sqrt(openP[0]),rollout_sd_inertia=np.sqrt(openP[1]),rollout_T=predT,
            success=int(not failed)))
        if failed:break
        execute(q1,q1,.05,False,item*10+3,'release')
        if failed:break
        tic=time.perf_counter();returnT=float(m.schedule(q1,q0,np.zeros(2),np.full(2,1e-20),True,c['margin_scale']))
        planning+=time.perf_counter()-tic
        execute(q1,q0,returnT,False,item*10+4,'returning')
        if failed:break
        completed+=1
    robot=sum(times.values())
    row=dict(seed=seed,N=N,family=family,method=method,**c,true_mass=actual[0],true_inertia=actual[1],
        completed=completed,success=int(completed==N),decision_reached=reached,probes=probes,
        gain_s=gain,robot_time_s=robot,planning_s=planning,J=robot+planning+10*(N-completed),
        **{f'{k}_s':v for k,v in times.items()},max_acceleration_ratio=maxa,max_velocity_ratio=maxv,
        probe_acceleration_ratio=probe_a,probe_velocity_ratio=probe_v,
        mass_covered=int(abs(theta[0]-actual[0])<=1.96*np.sqrt(P[0])),
        inertia_covered=int(abs(theta[1]-actual[1])<=1.96*np.sqrt(P[1])),
        mass_error=theta[0]-actual[0],inertia_error=theta[1]-actual[1],
        cap_count=cap_count,schedules=len(pads),max_margin_s=max(pads,default=0.),
        mean_rounding_residual_s=float(np.mean(rounding)) if rounding else 0.)
    return row,history,probe_prediction

def jobs():
    for family in ('excited','low_yaw'):
        for N in (1,5,20,40,60,100):
            yield 'extended','base',family,N,list(range(1001,1031)),METHODS,{}
    settings=[('noise10',{'noise':10.}),('noise100',{'noise':100.}),
        ('margin_half',{'margin_scale':.5}),('margin2',{'margin_scale':2.}),('margin4',{'margin_scale':4.}),
        ('inflation4',{'inflation':4.}),('inflation64',{'inflation':64.}),
        ('probe_fast',{'probe_T':.3,'allowance':.7}),('probe_slow',{'probe_T':.6,'allowance':1.3}),
        ('allowance07',{'allowance':.7}),('allowance11',{'allowance':1.1})]
    for label,c in settings:
        for family in ('excited','low_yaw'):
            for N in (20,60):
                yield 'sensitivity',label,family,N,list(range(1001,1011)),METHODS[:-1],c
    for label,c in [('friction075',{'fs':.75}),('friction125',{'fs':1.25}),('asymmetric',{'structure':1}),('physical_payload',{'physical_payload':True})]:
        for family in ('excited','low_yaw'):
            yield 'mismatch',label,family,20,list(range(1001,1031)),METHODS,c

def freeze():
    out=ROOT/'revision';out.mkdir(exist_ok=True)
    paths=[ROOT/'src/model_r1.py',ROOT/'src/revision_experiment.py']
    design=[dict(group=g,setting=l,family=f,N=N,seeds=seeds,methods=methods,settings={**DEFAULT,**c}) for g,l,f,N,seeds,methods,c in jobs()]
    record=dict(status='post-review exploratory extension; not original held-out preregistration',
        frozen_utc=datetime.now(timezone.utc).isoformat(),jobs=design,
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        environment=dict(python=platform.python_version(),platform=platform.platform(),cpu=platform.processor(),
            packages={x:importlib.metadata.version(x) for x in ('numpy','scipy','matplotlib','numba','llvmlite')}),
        notes=['Original policy unchanged at default parameters; new settings selected from review, not tuned to obtain benefit.',
        'Noise scales all sensor streams AND assumed observation variances by scale squared.',
        'Threshold baseline is our illustrative implementation, not a reimplementation of a published algorithm.',
        'Physical-payload scenario uses radius of gyration uniform 0.06-0.14 m; J=m*r_g^2.',
        'Hindsight comparator is best of two realized paired actions; not a physical or optimal-control bound.'])
    p=out/'post_review_protocol.json'
    if p.exists():raise RuntimeError('Freeze file already exists; preserve original record.')
    p.write_text(json.dumps(record,indent=2));print('Post-review protocol frozen',flush=True)

def verify_defaults():
    records=[]
    for seed in (11,1001,1004):
        for meth in ('passive','always_probe','batch_aware','ignore_passive','oracle'):
            old,_=original_batch(seed,5,'low_yaw',meth)
            new,_,_=batch(seed,5,'low_yaw',meth,{})
            keys=('robot_time_s','completed','success','probes','max_acceleration_ratio','max_velocity_ratio')
            differences={k:float(new[k])-float(old[k]) for k in keys}
            checks={k:abs(differences[k])<= (1e-10 if k=='robot_time_s' else 0.) for k in keys}
            records.append(dict(seed=seed,method=meth,checks=checks,differences=differences))
    assert all(all(r['checks'].values()) for r in records),records
    (ROOT/'revision/default_equivalence.json').write_text(json.dumps(records,indent=2))
    print('Default instrumentation matches original in 15 success/failure comparisons.',flush=True)

def run():
    out=ROOT/'revision';protocol=json.loads((out/'post_review_protocol.json').read_text())
    for name,h in protocol['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
    verify_defaults();batch(11,1,'excited','uncertainty_trigger',{})
    start=time.perf_counter();count=0
    with (out/'runs.csv').open('w',newline='') as f,(out/'items.csv').open('w',newline='') as fi,(out/'probe_forecasts.csv').open('w',newline='') as fp:
        writer=wi=wp=None
        for g,label,family,N,seeds,methods,c in jobs():
            for seed in seeds:
                for meth in methods:
                    row,hist,probe=batch(seed,N,family,meth,c)
                    key=dict(group=g,setting=label,seed=seed,N=N,family=family,method=meth)
                    row={'group':g,'setting':label,**row}
                    if writer is None:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader()
                    writer.writerow(row);count+=1
                    for h in hist:
                        it={**key,**h}
                        if wi is None:wi=csv.DictWriter(fi,fieldnames=list(it));wi.writeheader()
                        wi.writerow(it)
                    if probe:
                        pr={**key,**dict(zip(['pred_sd_mass','pred_sd_inertia','sd_mass','sd_inertia'],probe))}
                        if wp is None:wp=csv.DictWriter(fp,fieldnames=list(pr));wp.writeheader()
                        wp.writerow(pr)
            f.flush();fi.flush();fp.flush()
            print(f'{g}/{label}/{family}/N={N}: {count} batches, {time.perf_counter()-start:.1f}s',flush=True)
    print('All post-review simulations finished',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','run']);a=p.parse_args()
    freeze() if a.command=='freeze' else run()
