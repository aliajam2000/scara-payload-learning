"""Independent physical identities, integration, and closed-loop checks."""
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from tests.reference_model import Robot
from .model import mass,bias,inverse,accel,rk4,segment,pose,schedule,probe_decision
from .experiment import scenario,PRIOR,PRIOR_VAR

def validate(outdir):
    root=Path(__file__).resolve().parents[1]
    r=Robot(json.loads((root/'robot_config.json').read_text()))
    rng=np.random.default_rng(701); h=1e-6
    errors=dict(independent_energy=0.,reference_mass=0.,christoffel=0.,inverse_forward=0.,regressor=0.)
    mineig=1e9; christoffel_by_joint=np.zeros(4);regressor_by_joint=np.zeros(4)
    for i in range(200):
        q=rng.uniform([-1.5,-2.,.04,-1.],[1.5,2.,.25,1.]); v=rng.normal(0,.4,4); a=rng.normal(0,1,4)
        p=rng.uniform([.2,.002],[1.6,.025]); M=mass(q,p)
        mineig=min(mineig,float(np.linalg.eigvalsh(M)[0]))
        errors['independent_energy']=max(errors['independent_energy'],float(abs(.5*v@M@v-r.kinetic_energy_independent(q,v,p))))
        errors['reference_mass']=max(errors['reference_mass'],float(np.max(abs(M-r.mass(q,p)))))
        dM=np.stack([(mass(q+h*np.eye(4)[k],p)-mass(q-h*np.eye(4)[k],p))/(2*h) for k in range(4)],axis=2)
        cn=np.zeros(4)
        for j in range(4):
            for k in range(4):
                for l in range(4): cn[j]+=.5*(dM[j,k,l]+dM[j,l,k]-dM[k,l,j])*v[k]*v[l]
        christoffel_by_joint=np.maximum(christoffel_by_joint,abs(cn-r.coriolis(q,v,p)))
        errors['christoffel']=max(errors['christoffel'],float(max(abs(cn-r.coriolis(q,v,p)))))
        tau=inverse(q,v,a,p)
        errors['inverse_forward']=max(errors['inverse_forward'],float(max(abs(accel(q,v,tau,p)-a))))
        residual=tau-inverse(q,v,a,np.zeros(2))-r.payload_regressor(q,v,a)@p
        regressor_by_joint=np.maximum(regressor_by_joint,abs(residual))
        errors['regressor']=max(errors['regressor'],float(max(abs(residual))))
    x0=np.array([.2,1.,.15,-.5,.4,-.2,.0,.3]);p=np.array([1.2,.012]);tau=np.array([.3,.1,19.,.02])
    sol=solve_ivp(lambda t,x:np.r_[x[4:],r.forward_dynamics(x[:4],x[4:],tau,p)],
                  [0,.05],x0,method='DOP853',rtol=1e-12,atol=1e-14)
    x=x0.copy()
    for k in range(25):x=rk4(x,tau,p,.002,1.)
    independent_integrator_error=float(max(abs(x-sol.y[:,-1])))
    comparisons=[]
    for seed in (11,12,13):
        for family in ('excited','low_yaw'):
            actual,q0,q1=scenario(seed,family)
            T=float(schedule(q0,q1,PRIOR,PRIOR_VAR))
            args=(np.r_[q0,np.zeros(4)],q0,q1,T,PRIOR,PRIOR_VAR,True,actual,.002,seed,1.,0.)
            a=segment(*args,1);b=segment(*args,2)
            comparisons.append(dict(seed=seed,family=family,time_difference_s=abs(a[3]-b[3]),
                 position_difference_mm=float(np.linalg.norm(pose(a[0][:4])[:3]-pose(b[0][:4])[:3])*1000),
                 yaw_difference_deg=float(abs(pose(a[0][:4])[3]-pose(b[0][:4])[3])*180/np.pi),
                 state_difference=[float(z) for z in abs(a[0]-b[0])],
                 same_success=bool(a[4]==b[4]),success=bool(a[4]),
                 estimate_difference=[float(z) for z in abs(a[1]-b[1])]))
    # Decision cannot depend on true payload: its API takes only belief and task.
    # N=1 cannot repay a 0.9 s probe within the configured speed margin.
    _,q0,q1=scenario(11,'excited')
    decision,gain=probe_decision(1,PRIOR,PRIOR_VAR,q0,q1,.002)
    gates=dict(model_identities=max(errors.values())<1e-7,positive_mass=mineig>0,
               independent_integrator=independent_integrator_error<1e-6,
               substep_position=max(c['position_difference_mm'] for c in comparisons)<.1,
               substep_yaw=max(c['yaw_difference_deg'] for c in comparisons)<.05,
               substep_success=all(c['same_success'] and c['success'] for c in comparisons),
               short_batch_no_probe=not bool(decision))
    report=dict(status='PASS' if all(gates.values()) else 'FAIL',random_configurations=200,
                errors=errors,minimum_mass_eigenvalue=mineig,
                christoffel_by_joint=christoffel_by_joint.tolist(),regressor_by_joint=regressor_by_joint.tolist(),
                effort_units=['N m','N m','N','N m'],
                independent_integrator_state_error=abs(x-sol.y[:,-1]).tolist(),
                state_units=['rad','rad','m','rad','rad/s','rad/s','m/s','rad/s'],
                independent_integrator_max_state_error=independent_integrator_error,
                substep_comparisons=comparisons,gates={k:bool(v) for k,v in gates.items()},
                limitations='Synthetic model consistency, not hardware validation. Six noiseless transfer substep checks; no continuous-time safety proof.')
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if report['status']!='PASS':raise RuntimeError('Validation failed')

if __name__=="__main__":
    validate(Path(__file__).resolve().parents[1]/"revision/numerics")
