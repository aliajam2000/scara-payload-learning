# Post-review methods and provenance

The current manuscript is `paper/manuscript.pdf`. The original baseline simulator, experiment, protocol and `results/` data remain unchanged. `docs/METHODS.md` describes that historical release; the current manuscript and the post-review protocol define the extension.

## What changed

`src/model_r1.py` exposes noise scale, uncertainty-margin multiplier, observation-variance inflation, probe duration/allowance and plant friction mismatch. Default values preserve the original model. `src/revision_experiment.py` instruments component times and predicted/realized uncertainty, adds an illustrative uncertainty trigger, and logs each loaded transfer. Original behavior was checked in 15 paired runs including startup failures. Only regrouped time sums differ, at machine precision. The pre-grid tolerance amendment is documented and the initial freeze is retained.

The main protocol has 5,800 batches: 2,160 nominal horizon-extension, 2,200 sensitivity and 1,440 matched mismatch/physical-payload batches. Conditions were selected from the review; they are exploratory. Reused seed identities are not independent replications. After inspecting noise10 N=20/60, a separately recorded sequential refinement added 250 runs at N=5,10,15,25,30 in low yaw, giving 6,050 total post-review batches. This refinement is exploratory, not independent confirmation. No positive result was required for accepting a condition. All runs, including failed probes and pre-decision failures, are retained.

## Constants and units

The integral gain is k0*omega², with k0=6 s^-1 (not 6*omega³). Integral-state clips are 0.02 rad s or 0.02 m s. The margin has mass coefficient 0.16 s/kg and inertia coefficient 0.16 s, and includes a square root around sigma_J/(Jw0+Jhat). The initial margin is 0.181192885 s; it is not a universal maximum. These asymmetric engineering choices are preserved rather than silently replaced in an existing experiment.

Original constants were fixed before the held-out run. The available record establishes the final values and the 120 development outcomes, but cannot reconstruct every historical tuning choice. The factor 16 is an inflation heuristic, not a calibrated likelihood. No retrospective claim of optimal tuning is made.

The two probe legs are quintic wrist motions of 0.6 rad and back. Both scalar regressors contribute: gravity loading yields mass information even with zero commanded vertical motion. The 0.9 s allowance approximates commanded motion plus settling; realized probe time is recorded separately from the *net* active-minus-passive difference.

## Interpretation of analysis

Conditional robot-time differences use pairs where both methods finish. The separate decision-reaching statistic includes post-decision failures and must be read with completion counts. Main failure-adjusted decisions/regret use robot time + 10 s per unfinished item. No conditioning can turn a failed action into a successful policy; failure penalties and probe constraint ratios remain available.

Bootstrap unit: scenario seed, paired within condition, 10,000 resamples. The same physical scenarios recur across horizon and family. Bootstrap intervals are descriptive for the stated sampling distribution; the highly simplified startup failure is not a hardware-reliability estimate.

Hindsight chooses between the two realized, paired, fixed actions (probe/no probe). It is an optimistic offline comparator affected by realized noise, not an online optimum. Agreement tolerates one 2 ms sample of cost difference. Parameter coverage counts describe inflated variance intervals, not calibrated Bayesian posteriors. Repeated per-item forecast residuals are descriptive and correlated.

The empirical passive-minus-known-payload gap is a diagnostic for this heuristic, not a mathematical upper bound on possible improvement. Rounding and effort screening can alter the cost channel. The logged cap count refers to loaded-transfer schedule calls only; the original source retains exact fallback and rounding semantics.

## Reproduction

- `python revision.py analyze` regenerates all revised figures and analysis from supplied raw runs.
- `python revision.py verify` checks recorded counts, keys, frozen code hashes, action consistency and accounting identities.
- `python revision.py rerun` preserves the existing raw CSVs in a timestamped local directory and reruns all 6,050 batches, then analyzes them.
- `python -m src.revision_validation` repeats componentwise numerical checks.
- `python run.py demo --out demo_output` runs the original six-method smoke demonstration.

No Windows execution, hardware experiment, public repository publication or conference submission is claimed.
