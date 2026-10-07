"""Synthetic centered-payload RRPR SCARA, SI units. No hardware safety claim."""
import numpy as np
from numba import njit

EFFORT = np.array([25., 18., 80., 3.])
VLIM = np.array([4., 4., .8, 6.])
ALIM = np.array([25., 25., 5., 40.])
QMIN = np.array([-2.8, -2.8, .02, -2*np.pi])
QMAX = np.array([2.8, 2.8, .30, 2*np.pi])
WN = np.array([18., 20., 30., 24.])
BV = np.array([.08, .06, 2., .01])
BC = np.array([.03, .025, .1, .005])
QSIG = np.array([1e-5, 1e-5, 2e-6, 1e-5])
VSIG = np.array([.001, .001, .0002, .001])

@njit(cache=True)
def mass(q, p):
    mt=.8+p[0]; b=2*.35*.125+mt*.35*.25
    d=2*.25**2/12+2*.125**2+mt*.25**2
    a=3*.35**2/12+3*.175**2+2*.35**2+mt*.35**2+d
    M=np.zeros((4,4)); c=np.cos(q[1])
    M[0,0]=a+2*b*c+.008; M[0,1]=d+b*c; M[1,0]=M[0,1]
    M[1,1]=d+.004; M[2,2]=mt; M[3,3]=.001
    for i in (0,1,3):
        for j in (0,1,3): M[i,j]+=.008+p[1]
    return M

@njit(cache=True)
def friction(v): return BV*v+BC*np.tanh(v/.02)

@njit(cache=True)
def bias(q,v,p):
    h=-(2*.35*.125+(.8+p[0])*.35*.25)*np.sin(q[1])
    return np.array([h*(2*v[0]*v[1]+v[1]**2),-h*v[0]**2,(.8+p[0])*9.81,0.])

@njit(cache=True)
def inverse(q,v,a,p): return mass(q,p)@a+bias(q,v,p)+friction(v)

@njit(cache=True)
def accel(q,v,tau,p,friction_scale=1.):
    return np.linalg.solve(mass(q,p),tau-bias(q,v,p)-friction_scale*friction(v))

@njit(cache=True)
def derivative(x,tau,p,fs):
    out=np.empty(8); out[:4]=x[4:]; out[4:]=accel(x[:4],x[4:],tau,p,fs)
    return out

@njit(cache=True)
def rk4(x,tau,p,dt,fs):
    k1=derivative(x,tau,p,fs); k2=derivative(x+dt*k1/2,tau,p,fs)
    k3=derivative(x+dt*k2/2,tau,p,fs); k4=derivative(x+dt*k3,tau,p,fs)
    return x+dt*(k1+2*k2+2*k3+k4)/6

@njit(cache=True)
def reference(t,T,q0,q1):
    u=min(max(t/T,0.),1.); dq=q1-q0
    return (q0+(10*u**3-15*u**4+6*u**5)*dq,
            (30*u**2-60*u**3+30*u**4)/T*dq,
            (60*u-180*u**2+120*u**3)/T**2*dq)

@njit(cache=True)
def pose(q):
    return np.array([.35*np.cos(q[0])+.25*np.cos(q[0]+q[1]),
                     .35*np.sin(q[0])+.25*np.sin(q[0]+q[1]),q[2],q[0]+q[1]+q[3]])

@njit(cache=True)
def segment(x,q0,q1,T,estimate,variance,learn,actual,dt,seed,fs=1.,noise=1.,substeps=1):
    """Online integral ID from noisy velocity and actuator effort, never true a.

    Fresh independent sensor stream per segment. Controller integrator resets
    at segment transitions. Estimation windows are non-overlapping 50 ms.
    Completion/constraint scoring uses plant truth, not available to policy.
    Returns state, belief, elapsed, success, saturation ratio, position/yaw
    errors, and max normalized speed/acceleration. Any limit violation fails.
    """
    np.random.seed(seed)
    theta=estimate.copy(); P=variance.copy(); integ=np.zeros(4)
    window=max(1,int(round(.05/dt))); wd=window*dt
    hold=max(1,int(np.ceil(.05/dt))); counter=0; violated=False; sat=0
    maxvr=0.; maxar=0.; target=pose(q1)
    vstart=x[4:]+noise*VSIG*np.random.randn(4)
    vm=vstart.copy(); area=np.zeros(2); steps=int(np.ceil((T+.8)/dt))
    pe=1e6; ye=1e6; done=False
    for k in range(steps):
        t=k*dt; qm=x[:4]+noise*QSIG*np.random.randn(4)
        qr,vr,ar=reference(t,T,q0,q1)
        error=qr-qm; trial=np.clip(integ+error*dt,-.02,.02)
        commanded=ar+WN**2*error+2*WN*(vr-vm)+6*WN**2*trial
        raw=inverse(qm,vm,commanded,theta)
        tau=np.minimum(np.maximum(raw,-EFFORT),EFFORT)
        if np.max(np.abs(raw)/EFFORT)<=1.: integ=trial
        else: sat+=1
        a=accel(x[:4],x[4:],tau,actual,fs)
        maxvr=max(maxvr,np.max(np.abs(x[4:])/VLIM))
        maxar=max(maxar,np.max(np.abs(a)/ALIM))
        if np.any(x[:4]<QMIN) or np.any(x[:4]>QMAX): violated=True
        # Torque integral uses held actuator effort and trapezoidal friction.
        xn=x.copy()
        for sub in range(substeps): xn=rk4(xn,tau,actual,dt/substeps,fs)
        vn=xn[4:]+noise*VSIG*np.random.randn(4)
        fm=.5*(friction(vm)+friction(vn))
        area[0]+=dt*(tau[2]+noise*.2*np.random.randn()-fm[2])
        area[1]+=dt*(tau[3]+noise*.01*np.random.randn()-fm[3])
        if (k+1)%window==0:
            if learn:
                dv=vn-vstart
                Y=np.array([dv[2]+9.81*wd,dv[0]+dv[1]+dv[3]])
                z=np.array([area[0]-.8*Y[0],area[1]-.008*Y[1]-.001*dv[3]])
                # Conservative, approximate EIV/noise inflation; not a bound.
                R=np.array([16*((.2**2)*dt*wd+2*((.8+theta[0])*.0002)**2),
                            16*((.01**2)*dt*wd+6*((.008+theta[1])*.001)**2)])
                for j in range(2):
                    gain=P[j]*Y[j]/(R[j]+Y[j]**2*P[j])
                    theta[j]+=gain*(z[j]-Y[j]*theta[j]); P[j]*=1-gain*Y[j]
                theta[0]=min(max(theta[0],.05),2.)
                theta[1]=min(max(theta[1],.0005),.03)
            area[:]=0.; vstart=vn.copy()
        x=xn; vm=vn
        pp=pose(x[:4]); pe=np.linalg.norm(pp[:3]-target[:3])
        ye=abs((pp[3]-target[3]+np.pi)%(2*np.pi)-np.pi)
        if (k+1)*dt>=T-1e-10:
            if pe<=.001 and ye<=np.pi/360: counter+=1
            else: counter=0
            if counter>=hold: done=True; break
        if not np.all(np.isfinite(x)) or np.max(np.abs(x))>1e5: break
    maxvr=max(maxvr,np.max(np.abs(x[4:])/VLIM))
    violated=violated or np.any(x[:4]<QMIN) or np.any(x[:4]>QMAX)
    success=done and not violated and maxvr<=1. and maxar<=1.
    return x,theta,P,(k+1)*dt,success,sat/(k+1),pe,ye,maxvr,maxar

@njit(cache=True)
def schedule(q0,q1,theta,P,uncertainty=True):
    """Frozen reference-screening heuristic, not a certified safe optimizer."""
    sd=np.sqrt(P); pad=0.
    if uncertainty: pad=.16*sd[0]+.16*np.sqrt(sd[1]/(.008+theta[1]))
    envelope=theta+2*sd if uncertainty else theta.copy()
    envelope[0]=min(envelope[0],2.); envelope[1]=min(envelope[1],.03)
    for n in range(36):
        T=.55+.025*n
        good=True
        for k in range(31):
            q,v,a=reference(T*k/30,T,q0,q1)
            if np.max(np.abs(v)/VLIM)>.8 or np.max(np.abs(a)/ALIM)>.7:
                good=False; break
            if np.max(np.abs(inverse(q,v,a,envelope))/EFFORT)>.75:
                good=False; break
        if good: return np.ceil((T+pad)/.025)*.025
    return 1.8

@njit(cache=True)
def forecast(P,theta,q0,q1,T,dt):
    """Expected information under commanded motion; ignores bias/correlation."""
    out=P.copy(); wd=.05
    R=np.array([16*(.2**2*dt*wd+2*((.8+theta[0])*.0002)**2),
                16*(.01**2*dt*wd+6*((.008+theta[1])*.001)**2)])
    for k in range(int(T/wd)):
        _,v0,_=reference(k*wd,T,q0,q1); _,v1,_=reference((k+1)*wd,T,q0,q1)
        dv=v1-v0; y=np.array([dv[2]+9.81*wd,dv[0]+dv[1]+dv[3]])
        out=1/(1/out+y*y/R)
    return out

@njit(cache=True)
def forecast_batch(N,theta,P,q0,q1,dt):
    cost=0.; pp=P.copy()
    for k in range(N):
        T=schedule(q0,q1,theta,pp)
        cost+=T+.05
        pp=forecast(pp,theta,q0,q1,T,dt)
    return cost

@njit(cache=True)
def probe_decision(N,theta,P,q0,q1,dt,ignore_passive=False):
    qp=q0.copy(); qp[3]+=.6
    pp=forecast(P,theta,q0,qp,.4,dt)
    pp=forecast(pp,theta,qp,q0,.4,dt)
    overhead=.9
    if ignore_passive:
        gain=N*(schedule(q0,q1,theta,P)-schedule(q0,q1,theta,pp))-overhead
    else:
        gain=forecast_batch(N,theta,P,q0,q1,dt)-forecast_batch(N,theta,pp,q0,q1,dt)-overhead
    return gain>0.,gain
