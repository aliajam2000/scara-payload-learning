> Historical methods for the preserved original release. For current results, conditioning, extensions and provenance, use the revised manuscript and REVISION_METHODS.md.

# Experimental methods and exact interpretation

## Scope

Each batch repeats one obstacle-free loaded transfer, followed by an unloaded return. Objects within a batch share mass and centered yaw inertia. A batch starts at rest; subsequent segments retain the actual position and velocity. A 50 ms commanded hold plus at least 50 ms in tolerance models each grasp/release dwell. The payload switches instantaneously at the beginning of those dwell segments; contact and gripper mechanics are not simulated. Loaded and empty references connect the endpoints directly in joint space. There is no separate obstacle-clearance, approach or retreat planner.

Nominal endpoints are `[-0.65,1.15,0.10,-0.50]` and `[0.45,0.75,0.18,0.20]`; the goal's first two joints receive independent ±0.06 rad perturbations. The low-yaw family changes the wrist goal so net tool yaw displacement is 0.15 rad. Payload mass and yaw inertia are independent uniform draws from [0.2,1.6] kg and [0.002,0.025] kg m². This is a synthetic parameter distribution, not a fitted population of commercial objects.

## Controller

All methods use saturated computed torque with PD and integral terms. Natural frequencies are [18,20,30,24] s⁻¹, derivative gain 2ω, proportional gain ω², and integral gain 6ω². The integral state is clipped to ±0.02 in each coordinate's error-time units, frozen while any actuator saturates, and reset at segment transitions. Resetting is part of the common controller. The fixed-model comparator therefore has integral compensation for persistent load error; it is not the flawed gravity-offset comparator in the early pilot.

The zero-order-held command is integrated by RK4 at 2 ms. Position noise standard deviations are [10⁻⁵,10⁻⁵,2×10⁻⁶,10⁻⁵] in SI joint units; velocity deviations [0.001,0.001,0.0002,0.001]. Velocity is an idealized separately observed noisy signal, not a numerically differentiated noisy position. Effort readings add 0.2 N vertical and 0.01 N m wrist noise. Other joints' effort readings are not used by the estimator. Noise is independent Gaussian per sample; no bias or time correlation is imposed.

## Online integral estimation

Let φ=q1+q2+q4. Over each non-overlapping 50 ms window:

```
Ym = Δvz + g Δt
zm = ∫(τz − fz) dt − mc Ym = mp Ym
YJ = Δφdot
zJ = ∫(τ4 − f4) dt − Jw0 YJ − Ir4 Δq4dot = Jp YJ
```

Effort integration is rectangular for held torque, friction trapezoidal on noisy velocity endpoints. These identities use measured velocities and effort, not true acceleration. Each scalar update uses K=P Y/(R+Y²P), θ←θ+K(z−Yθ), P←(1−KY)P. Initial means are [0.8,0.012], initial standard deviations [0.5,0.008]. Estimates are projected to mass [0.05,2] and inertia [0.0005,0.03]. Covariance is not corrected for projection.

With sample step h and window Δ=0.05, the assumed observation variances are:

```
Rm = 16[(0.2²) h Δ + 2((mc + mhat) 0.0002)²]
RJ = 16[(0.01²) h Δ + 6((Jw0 + Jhat) 0.001)²]
```

The factor 16 is a fixed engineering inflation. This is approximate regression with noisy regressors, shared window endpoints, unmodeled friction-error contributions and covariance projection mismatch. It is not an exact Bayesian posterior or a rigorous confidence set. Updates occur during every loaded segment, including the mandatory grasp dwell, every 50 ms. The updated parameters immediately enter the controller. Empty returns do not update payload estimates. The same payload belief persists across objects within the batch.

## Duration selection

For quintic point-to-point paths, candidate durations run from 0.55 to 1.425 s in 0.025 s increments. At 31 reference samples, a candidate must satisfy 80% velocity, 70% acceleration and 75% torque limits. Torque screening uses the estimate plus two approximate standard deviations, capped at [2,0.03]. A duration margin is then added:

```
margin = 0.16 σm + 0.16 sqrt(σJ/(0.008 + Jhat))
T = ceil((screened_duration + margin)/0.025) * 0.025
```

The coefficients have the units needed to yield seconds. If no candidate passes, return 1.8 s. These are fixed conservative heuristic rules, not an optimal time-scaling solution. The uncertainty margin is not task-sensitivity weighted; this can overvalue learning irrelevant inertia. A capped upper parameter vector is not a worst-case proof over the parameter set. Actual position, velocity and acceleration limits are checked in the plant after execution; a limit violation makes the batch unsuccessful even if it reached the endpoint.

## Separate probe and decision

The only optional probe is a 0.6 rad wrist excursion and return, with 0.4 s commanded duration per leg and settling on each leg. It is considered once after the first grasp dwell. The information predictor integrates commanded reference velocity changes using the same regression variance model, with means fixed at the current estimates. It does not predict the realized observation, controller tracking error or future estimate drift.

The batch-aware rule forecasts the sum of loaded durations plus 50 ms settling over N items, shrinking covariance after each predicted normal transfer. It subtracts the corresponding forecast after the two probe legs, then subtracts a 0.9 s probe allowance. Probe only when the difference is positive. This is a certainty-equivalent covariance rollout, not a full Bayes-adaptive optimal-control solution. Mandatory future grasp information is omitted from the rollout, making passive learning forecast somewhat conservative. Common empty-return/grasp/release costs cancel in this surrogate comparison. The true measured overhead, including any extra settling, is counted in the actual experiment. Predicted settling/feasibility is approximate; no risk constraint is claimed.

The `ignore_passive` ablation replaces the rollout with N times the immediate duration reduction minus 0.9 s. It isolates the error of pretending the no-probe estimate would remain equally uncertain for the entire batch.

## Comparators

1. Fixed nominal: fixed prior mean and uncertainty, no learning, same integral controller and duration rule.
2. Passive: online estimation during useful task/grasp motions; never add a probe.
3. Always probe: same estimator, always execute the two-leg probe.
4. Batch aware: same estimator plus the above covariance rollout.
5. Ignore passive: same estimator in reality, but omit future passive learning in the probe decision.
6. Oracle: known true payload, negligible uncertainty, same controller and duration rule. This is a diagnostic reference, not a deployable method or a mathematically optimal lower bound.

The passive comparator is the principal baseline. No claim is made to outperform a reimplementation of published trajectory-optimized dual control or safe identification; those methods are related work, not numerical comparators.

## Endpoints, failures, computation and statistics

Completion requires true tool position within 1 mm and yaw within 0.5 degrees for 50 ms after the commanded motion, with at most 0.8 s extra settling. Terminal truth is used by simulator scoring, not the estimator. Failure stops the batch; all unfinished items receive a 10 s penalty, including the currently failed item. Raw elapsed time, completed items, failures and penalized time are retained. Constraints are sampled; no intersample guarantee is made.

Measured planner time includes duration screening and probe-decision evaluation after JIT warmup, and is added to the primary cost. This is host-dependent execution time. Controller/estimator CPU time is not added; the study does not demonstrate real-time schedulability. There is no training phase whose time is being hidden.

Development: seeds 11–15, 120 batches. Held-out: seeds 1001–1030, N in {1,5,20}, two task families, six methods = 1,080 batches. Stress: seeds 2001–2010, N=5, both families, six methods = 120 batches with actual friction multiplied by 1.25 and nominal estimator friction unchanged. These stress results are out-of-model sensitivity checks, not a second independent proof of efficacy.

For each condition, method-minus-passive costs are paired by seed. Report the mean and percentile 95% interval from 10,000 bootstrap draws of 30 seed pairs. Exact binomial success intervals are also reported; zero observed failures among 30 trials cannot establish near-perfect reliability. Seeds are reused across batch sizes and families, so pooled counts must not be used as independent trials for an overall confidence interval. Approximate 95% marginal parameter intervals are assessed by empirical endpoint coverage; oracle/fixed-model coverage is not a calibrated inference claim.
