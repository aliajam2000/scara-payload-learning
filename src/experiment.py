"""Reproducible paired batch experiments. Run through run.py."""
import csv
import json
import time
from pathlib import Path
import numpy as np
from .model import segment, schedule, probe_decision

METHODS=['fixed_nominal','passive','always_probe','batch_aware','ignore_passive','oracle']
PRIOR=np.array([.8,.012]); PRIOR_VAR=np.array([.5**2,.008**2])

def scenario(seed, family):
    rng=np.random.default_rng(seed)
    actual=np.array([rng.uniform(.2,1.6),rng.uniform(.002,.025)])
    q0=np.array([-.65,1.15,.10,-.5])
    q1=np.array([.45,.75,.18,.20])
    q1[:2]+=rng.uniform(-.06,.06,2)
    if family=='low_yaw': q1[3]=q0[0]+q0[1]+q0[3]+.15-q1[0]-q1[1]
    return actual,q0,q1

def batch(seed,N,family,method,dt=.002,fs=1.):
    actual,q0,q1=scenario(seed,family)
    theta=actual.copy() if method=='oracle' else PRIOR.copy()
    P=np.full(2,1e-20) if method=='oracle' else PRIOR_VAR.copy()
    learn=method not in ('fixed_nominal','oracle')
    x=np.r_[q0,np.zeros(4)]; robot_time=0.; planning=0.; completed=0
    probes=0; failed=False; sat=0.; max_v=0.; max_a=0.; max_pe=0.; max_ye=0.
    gain=float('nan'); first_T=float('nan'); initial_sd=np.sqrt(P).copy()
    trace=[]

    def execute(a,b,T,loaded,stream):
        nonlocal x,theta,P,robot_time,failed,sat,max_v,max_a,max_pe,max_ye
        est=theta if loaded else np.zeros(2)
        var=P if loaded else np.full(2,1e-20)
        out=segment(x,a,b,T,est,var,learn and loaded,
                    actual if loaded else np.zeros(2),dt,seed*10000+stream,fs)
        x=out[0]
        if loaded: theta,P=out[1],out[2]
        robot_time+=out[3]; failed=failed or not out[4]
        sat=max(sat,out[5]); max_pe=max(max_pe,out[6]); max_ye=max(max_ye,out[7])
        max_v=max(max_v,out[8]); max_a=max(max_a,out[9])

    for item in range(N):
        # Mandatory grasp dwell is simulated and can provide passive information.
        execute(q0,q0,.05,True,item*10+1)
        if failed: break
        if item==0:
            initial_sd=np.sqrt(P).copy()
            tic=time.perf_counter()
            take=False
            if method=='always_probe': take=True
            elif method in ('batch_aware','ignore_passive'):
                take,gain=probe_decision(N,theta,P,q0,q1,dt,method=='ignore_passive')
            planning+=time.perf_counter()-tic
            if take:
                probes=1; qp=q0.copy(); qp[3]+=.6
                execute(q0,qp,.4,True,9001)
                if not failed: execute(qp,q0,.4,True,9002)
                if failed: break
        tic=time.perf_counter()
        T=float(schedule(q0,q1,theta,P))
        planning+=time.perf_counter()-tic
        if item==0: first_T=T
        execute(q0,q1,T,True,item*10+2)
        trace.append([item+1,T,*theta,*np.sqrt(P)])
        if failed: break
        # Known unloading event; same physical position/velocity, empty model.
        execute(q1,q1,.05,False,item*10+3)
        if failed: break
        tic=time.perf_counter()
        return_T=float(schedule(q1,q0,np.zeros(2),np.full(2,1e-20)))
        planning+=time.perf_counter()-tic
        execute(q1,q0,return_T,False,item*10+4)
        if failed: break
        completed+=1
    # An abort never appears artificially fast: 10 s for each unfinished item.
    penalty=10.*(N-completed)
    row=dict(seed=seed,N=N,family=family,method=method,dt=dt,friction_scale=fs,
             true_mass=actual[0],true_inertia=actual[1],completed=completed,
             success=int(completed==N),robot_time_s=robot_time,planning_s=planning,
             penalized_time_s=robot_time+planning+penalty,probes=probes,
             predicted_probe_gain_s=gain,first_duration_s=first_T,
             estimate_mass=theta[0],estimate_inertia=theta[1],
             sd_mass=np.sqrt(P[0]),sd_inertia=np.sqrt(P[1]),
             post_grasp_sd_mass=initial_sd[0],post_grasp_sd_inertia=initial_sd[1],
             mass_covered=int(abs(theta[0]-actual[0])<=1.96*np.sqrt(P[0])),
             inertia_covered=int(abs(theta[1]-actual[1])<=1.96*np.sqrt(P[1])),
             max_segment_saturation=sat,max_velocity_ratio=max_v,max_acceleration_ratio=max_a,
             max_terminal_position_mm=1000*max_pe,max_terminal_yaw_deg=np.rad2deg(max_ye))
    return row,trace

def warmup():
    batch(11,1,'excited','batch_aware')
    batch(11,1,'excited','ignore_passive')

def run_grid(outdir, seeds, Ns, families, methods,dt=.002,fs=1.,name='batches'):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    warmup(); rows=[]; traces={}; start=time.perf_counter()
    path=outdir/f'{name}.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=None
        for family in families:
            for N in Ns:
                for seed in seeds:
                    for method in methods:
                        row,tr=batch(seed,N,family,method,dt,fs)
                        if writer is None:
                            writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader()
                        writer.writerow(row);f.flush();rows.append(row)
                        if seed==seeds[0]: traces[f'{family}_{N}_{method}']=tr
                print(f'{name}: {family}, N={N}: {len(rows)} batches, {time.perf_counter()-start:.1f} s',flush=True)
    (outdir/f'{name}_traces.json').write_text(json.dumps(traces,indent=2))
    return rows
