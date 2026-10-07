"""Synthetic rigid RRPR SCARA; SI units, q3 upward, centered axisymmetric payload.

No manufacturer fidelity, learned policy, or statistical safety guarantee is claimed.
See docs/MODEL.md for the independent energy derivation and assumptions.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np


ROOT = Path(__file__).resolve().parent


def load_config():
    return json.loads((ROOT / "config.json").read_text())


def wrap(a):
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi


@dataclass
class Robot:
    p: dict

    @classmethod
    def default(cls):
        return cls(load_config()["robot"])

    def fk(self, q):
        l1, l2 = self.p["l1"], self.p["l2"]
        return np.array([l1*np.cos(q[0])+l2*np.cos(q[0]+q[1]),
                         l1*np.sin(q[0])+l2*np.sin(q[0]+q[1]),
                         q[2], q[0]+q[1]+q[3]])

    def ik(self, pose, branch=1):
        """Geometric solution only. Caller checks joint limits and continuity."""
        if branch not in (-1, 1):
            raise ValueError("branch must be +1 or -1")
        x, y, z, phi = pose
        l1, l2 = self.p["l1"], self.p["l2"]
        c2 = (x*x+y*y-l1*l1-l2*l2)/(2*l1*l2)
        if abs(c2) > 1+1e-12:
            raise ValueError("Target outside planar geometric workspace")
        q2 = branch*np.arccos(np.clip(c2, -1, 1))
        q1 = np.arctan2(y,x)-np.arctan2(l2*np.sin(q2),l1+l2*np.cos(q2))
        return np.array([q1, q2, z, phi-q1-q2])

    def jacobian(self, q):
        l1, l2 = self.p["l1"], self.p["l2"]
        a,b = q[0],q[0]+q[1]
        return np.array([[-l1*np.sin(a)-l2*np.sin(b),-l2*np.sin(b),0,0],
                         [l1*np.cos(a)+l2*np.cos(b),l2*np.cos(b),0,0],
                         [0,0,1,0],[1,1,0,1]], dtype=float)

    def mass(self, q, payload):
        mp, jp = payload
        p=self.p
        l1,l2=p["l1"],p["l2"]
        r1,r2=l1/2,l2/2
        i1,i2=p["m1"]*l1*l1/12,p["m2"]*l2*l2/12
        mt=p["carriage_mass"]+mp
        b=p["m2"]*l1*r2+mt*l1*l2
        d=i2+p["m2"]*r2*r2+mt*l2*l2
        a=i1+p["m1"]*r1*r1+p["m2"]*l1*l1+mt*l1*l1+d
        M=np.zeros((4,4))
        M[0,0]=a+2*b*np.cos(q[1])
        M[0,1]=M[1,0]=d+b*np.cos(q[1])
        M[1,1]=d
        M[2,2]=mt
        s=np.array([1.,1.,0.,1.])
        M+=(p["wrist_yaw_inertia"]+jp)*np.outer(s,s)
        M+=np.diag(p["rotor_inertias"])
        return M

    def coriolis(self, q, v, payload):
        p=self.p
        b=p["m2"]*p["l1"]*p["l2"]/2+(p["carriage_mass"]+payload[0])*p["l1"]*p["l2"]
        h=-b*np.sin(q[1])
        return np.array([h*(2*v[0]*v[1]+v[1]**2), -h*v[0]**2, 0.,0.])

    def gravity(self, payload):
        return np.array([0.,0.,(self.p["carriage_mass"]+payload[0])*self.p["gravity"],0.])

    def friction(self, v):
        p=self.p
        return np.array(p["viscous"])*v+np.array(p["coulomb"])*np.tanh(v/p["friction_smoothing"])

    def inverse_dynamics(self,q,v,a,payload,friction=True):
        return (self.mass(q,payload)@a+self.coriolis(q,v,payload)+self.gravity(payload)
                +(self.friction(v) if friction else 0))

    def forward_dynamics(self,q,v,tau,payload,friction=True):
        return np.linalg.solve(self.mass(q,payload), tau-self.coriolis(q,v,payload)
                               -self.gravity(payload)-(self.friction(v) if friction else 0))

    def payload_regressor(self,q,v,a):
        """tau - tau(empty) = Y [payload mass, payload yaw inertia]."""
        l1,l2=self.p["l1"],self.p["l2"]
        c,s=np.cos(q[1]),np.sin(q[1])
        A=l1*l1+l2*l2+2*l1*l2*c
        B=l2*l2+l1*l2*c
        ym=np.array([A*a[0]+B*a[1]-l1*l2*s*(2*v[0]*v[1]+v[1]**2),
                     B*a[0]+l2*l2*a[1]+l1*l2*s*v[0]**2,
                     a[2]+self.p["gravity"], 0.])
        yj=np.array([1.,1.,0.,1.])*(a[0]+a[1]+a[3])
        return np.column_stack([ym,yj])

    def kinetic_energy_independent(self,q,v,payload):
        """Sum body translational/rotational energies; does not call mass()."""
        p=self.p; l1,l2=p["l1"],p["l2"]
        t1=np.array([-np.sin(q[0]),np.cos(q[0])])
        t2=np.array([-np.sin(q[0]+q[1]),np.cos(q[0]+q[1])])
        v1=(l1/2)*t1*v[0]
        v2=l1*t1*v[0]+(l2/2)*t2*(v[0]+v[1])
        vw=l1*t1*v[0]+l2*t2*(v[0]+v[1])
        T=.5*p["m1"]*(v1@v1)+.5*(p["m1"]*l1*l1/12)*v[0]**2
        T+=.5*p["m2"]*(v2@v2)+.5*(p["m2"]*l2*l2/12)*(v[0]+v[1])**2
        T+=.5*(p["carriage_mass"]+payload[0])*(vw@vw+v[2]**2)
        T+=.5*(p["wrist_yaw_inertia"]+payload[1])*(v[0]+v[1]+v[3])**2
        T+=.5*np.dot(p["rotor_inertias"],v*v)
        return T

