# Model specification and derivation — computational release 1.0

This is an original implementation of a deliberately simplified synthetic
benchmark. Constants are engineering choices, not measurements of a physical robot
or specifications of a commercial robot. Dynamics conventions follow the
standard Lagrangian formulation in Lynch & Park, Modern Robotics, Chapter 8:
https://modernrobotics.northwestern.edu/chapters/chapter8/

## Coordinates and scope

q = [q1, q2, z, q4]. Joint order: R-R-P-R. q1, q2, q4 are radians;
z is metres, positive upward. Effort vector is [N m, N m, N, N m].
The links rotate in a horizontal plane; the translating carriage sits at
the end of link 2. Tool yaw phi = q1 + q2 + q4; z directly denotes tool height.
The chosen ideal architecture has no xy/z inertial coupling. It is a fully
actuated, generally nonredundant model for [x, y, z, phi].

Assumptions: rigid links, uniform slender links 1 and 2, fixed base, aligned
vertical axes, concentrated carriage mass, ideal transmission inertias,
axisymmetric payload centered on the tool axis. Payload parameters are
theta = [m_p, J_p], mass and yaw moment of inertia about the tool axis.
J_p is independent of joint configuration. Off-axis centers of mass, compliance,
backlash, motor electrical dynamics, collisions, gripping and contact are absent.
There is no object slipping or payload change *within* an individual transfer.

The final experiment includes loaded transfer, mandatory grasp/release dwell and unloaded return, with continuous state. It omits contact mechanics and explicit approach/lift/lower waypoints. See METHODS.md for the exact batch protocol.

## Forward and inverse kinematics

x = l1 cos(q1) + l2 cos(q1+q2)

y = l1 sin(q1) + l2 sin(q1+q2)

z_tool = z; phi = q1 + q2 + q4.

c2 = (x^2 + y^2 - l1^2 - l2^2)/(2 l1 l2)

q2 = +/- acos(c2)

q1 = atan2(y,x) - atan2(l2 sin(q2), l1+l2 cos(q2))

q4 = phi-q1-q2.

The IK helper returns a geometric branch, not a joint-limit-safe or
collision-safe command. A future planner must select a continuous valid branch
and check all joint limits. Targets with |c2| > 1 are rejected. Yaw errors use
wrapped angular differences; translational and angular tolerances are separate.

## Energy and Lagrangian dynamics

Let r1=l1/2, r2=l2/2; Ii=mi li^2/12; mt=mc+mp;
Jw=Jw0+Jp; s=[1,1,0,1]^T; D=diag(rotor inertias).

Planar body velocities follow by differentiating their center positions:

- v1 = r1 [-sin(q1), cos(q1)] q1dot.
- v2 = l1 [-sin(q1), cos(q1)] q1dot
  + r2 [-sin(q1+q2), cos(q1+q2)] (q1dot+q2dot).
- vw = l1 [-sin(q1), cos(q1)] q1dot
  + l2 [-sin(q1+q2), cos(q1+q2)] (q1dot+q2dot).

Kinetic energy:

T = (m1 |v1|^2 + I1 q1dot^2 + m2 |v2|^2
    + I2 (q1dot+q2dot)^2 + mt (|vw|^2 + zdot^2)
    + Jw (q1dot+q2dot+q4dot)^2 + qdot^T D qdot)/2.

Potential energy: V = mt g z (constant horizontal-link terms omitted).

Applying d/dt(dT/dqdot) - dT/dq + dV/dq gives:

M(q,theta) qddot + c(q,qdot,theta) + g(theta) + f(qdot) = tau.

Define b=m2 l1 r2 + mt l1 l2,
d=I2+m2 r2^2+mt l2^2,
a=I1+m1 r1^2+m2 l1^2+mt l1^2+d.

The nonzero entries of M0 are:

M0_11 = a+2b cos(q2)

M0_12 = M0_21 = d+b cos(q2)

M0_22 = d; M0_33=mt.

M = M0 + Jw s s^T + D.

With h=-b sin(q2), velocity-product vector:

c = [h(2 q1dot q2dot + q2dot^2), -h q1dot^2, 0, 0]^T.

g = [0,0,mt g,0]^T.

Smooth friction uses f_i = bv_i qdot_i + bc_i tanh(qdot_i/eps_i).
The numeric smoothing values currently coincide (0.02) but have the appropriate
rad/s or m/s units for each joint. Joint 3 rotor entry is an effective mass,
currently zero; rotational rotor entries have kg m^2 units.

## Payload regressor

Subtract the empty-payload inverse dynamics:

tau - tau_empty = Y_m m_p + Y_J J_p.

Let A=l1^2+l2^2+2 l1 l2 cos(q2), B=l2^2+l1 l2 cos(q2).

Y_m = [
A q1ddot + B q2ddot - l1 l2 sin(q2)(2 q1dot q2dot+q2dot^2),
B q1ddot + l2^2 q2ddot + l1 l2 sin(q2) q1dot^2,
zddot + g,
0]^T.

Y_J = s (q1ddot+q2ddot+q4ddot).

At rest, mass is observable from vertical effort if gravity, unloaded mass,
friction and force offset are known. J_p is unobservable at rest. If tool yaw
has no angular acceleration, this ideal model has no J_p regressor signal.
This is an observability statement, not proof that a separate probe is useful:
ordinary task motion may already excite J_p enough.

The algebraic diagnostic whitens each effort row by its sensor standard
deviation. A dimensional unscaled condition number must not be used to claim
information quality. The final release uses two separate scalar integral regressions and reports their marginal errors rather than a dimensional condition number.


## Final implementation and verification

The controller, estimator, scheduling heuristic, sampling limits, noisy sensing and completion protocol are specified in METHODS.md. `src/validation.py` checks 200 randomized mass matrices against independently summed body energies, finite-difference Christoffel terms, the payload regressor and inverse-forward consistency. A separate SciPy DOP853 integration and six closed-loop plant-substep checks supplement those identities. `results/validation.json` contains actual errors and pass/fail gates. These checks establish numerical consistency of the chosen model, not validation against a real robot.
