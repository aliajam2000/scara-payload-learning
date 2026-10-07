# Response to independent pre-submission review

**Revised title:** Payload Probing with Passive Learning: Break-Even and Decision Regret in a SCARA Simulation

**Reviewed title:** Accounting for Passive Learning in Batch-Level Payload Probing: A SCARA Simulation Study

**Revision date:** 7 October 2026

This response is an author-side revision record, not a claim that the reviewer has accepted the changes. The supplied review was PDF-only and did not examine the code. We checked its numerical inferences against the implementation and retained disagreements where the evidence requires them.

## Main changes and result

The original simulator, frozen protocol and results are preserved. We added 5,800 batches under a separately recorded post-review protocol, then 250 explicitly sequential exploratory batches to refine a crossing observed in the noise study. These are 6,050 executions, **not 6,050 independent scenarios**. Main seeds are reused; none of this work is relabeled as new independent held-out confirmation.

- The nominal mean probe excess remains positive through N=100: 0.796 s (exciting) and 0.311 s (low yaw), conditional on 27 paired completions. Four nominal low-yaw scenarios at N=40,60,100 individually benefit; batch-aware misses them.
- With tenfold noise, low yaw and N=60, the probe saves 1.052 s [0.923, 1.194], across nine jointly successful scenarios. Batch-aware selects all nine. One of ten scenarios fails before the decision.
- The sampled mean changes sign between N=15 and 20 in that noisy regime; N=20 remains uncertain (net excess -0.026 s, interval [-0.099, 0.045]). N=15 and 25 bracket clearly opposite signs. Local interpolation gives about 19.2 items, a descriptive estimate only.
- Batch-aware over-probes at the noisy N=20 boundary and misses all seven beneficial doubled-margin N=60 scenarios. It is not presented as generally calibrated or superior.
- Fast probes cause additional failures; friction mismatch destroys mass-interval coverage in completed batches. These adverse results remain visible.

The revised PDF is eight pages in a generic two-column format. Venue-specific page limits, format, author details, license and disclosures remain outside this computational revision.

## Corrections to inferences in the review

1. Eq. (9) contains a square root. Its prior margin is 0.16*0.5 + 0.16*sqrt(0.008/0.020) = **0.181192885 s**, not 0.144 s. This is an initial value, not a universal maximum.
2. A wrist-only probe provides **both** scalar regressor contributions. Holding vertical position still gives Ym=g*Delta from gravity loading, so it also informs mass.
3. The measured two-leg probe takes **0.896 s**. The **0.796 s** exciting-task net excess is probe time minus 0.100 s downstream savings, not the full elapsed probe time.
4. The passive-minus-known-payload gap is an empirical diagnostic, not a universal upper bound; the known-payload scheduler is heuristic and not an optimal controller.
5. Deterministic failure conditional on a randomly drawn mass can still induce a legitimate sampling probability. We removed reliability-style headline reporting because this simplified distribution does not establish hardware reliability, not because a binomial model is categorically impossible.
6. The arXiv entry 2510.20483 does contain version 2 dated 29 September 2026. The citation was verified; process commentary about counting versions was removed.

## R1 — Headroom, decomposition and larger horizons

**Addressed, with corrections to the proposed interpretation.** Section 6.2 and Figure 1 report empirical paired headroom and explicit probe/downstream decomposition. At nominal N=20, passive-minus-known-payload gaps are 0.122 s [0.113, 0.131] exciting and 0.499 s [0.452, 0.545] low yaw. The probe takes 0.896 s and saves 0.100 or 0.477 s downstream. Horizons 40,60,100 show low-yaw savings plateau at 0.585 s; the mean does not cross zero. We do not extrapolate the small-N trend linearly.

Section 6.3 and Figure 2 locate a crossing neighborhood under tenfold noise, with the sequential design clearly identified. The prior margin and the probe's mass information are corrected as above. Data: `revision/headroom.csv`, `decomposition.csv`, `break_even_runs.csv`.

## R2 — Distinguish the rule from never-probe

**Addressed; favorable and unfavorable evidence both retained.** The noisy low-yaw N=60 condition has nine beneficial cases, all selected by batch-aware. At noisy N=20 it selects nine probes although only five benefit, giving agreement 5/9 and regret 0.040 s [0.012, 0.070]. At nominal low-yaw N=100 it misses four beneficial scenarios (agreement 23/27, mean regret 0.066 s, maximum 0.602 s). Under doubled margin at N=60 it misses seven beneficial cases (mean regret 0.559 s). Table 3 and `decision_quality.csv` report two-action hindsight comparisons; the full file includes passive, always-probe, batch-aware, ignore-passive and the uncertainty trigger.

This supports limited sensitivity and specificity in named regimes, not universal decision-rule validation. Hindsight is the best of two realized paired actions, not an online or optimal-control bound.

## R3 — Sensitivity to hand-set constants

**Addressed within a compact exploratory design.** At N=20 and 60, both families, seeds 1001–1010, we vary sensor noise 10/100, margin 0.5/2/4, inflation 4/64, probe-duration/allowance pairs (0.3,0.7) and (0.6,1.3) seconds, and allowance alone 0.7/1.1 seconds. Nominal references use matching first-ten seeds for the sensitivity plot. Results include all failures. The change in sign with noise, margin and inflation is reported, as are zero N=60 completions at noise scale 100.

The design is not factorial and does not characterize interactions. Changing probe duration with its corresponding allowance does not isolate those two factors. Data: `conditional_effects.csv`, `conditional_summary.csv`, `decision_quality.csv`, `sensitivity.pdf`.

## R4 — Ablation and baseline fairness

**Framing addressed; published-method replication remains a limitation.** The horizon-multiplied rule is explicitly an illustrative ablation, without a claim that a prior paper uses it. The extension includes an uncertainty-threshold trigger, sigma_J/(Jw0+Jhat)>0.2, and retains always-probe as a fixed-schedule baseline. We connect trigger-based learning to the literature but do not label our engineering threshold as Solowjow and Trimpe's algorithm. Several cells make this trigger identical to always-probe; that equivalence is disclosed.

No state-of-the-art numerical superiority claim is made. A full published dual-control or safe-identification reimplementation remains future research rather than an asserted completion.

## R5 — Matched friction mismatch and stress costs

**Addressed.** All 30 main seeds are used at N=20 for friction multipliers 0.75,1.25 and an asymmetric smooth friction term. Each non-oracle method completes 27/30, and batch-aware remains physically identical to passive. Low-yaw always-probe excess is 0.418,0.423,0.421 s respectively. All method costs and coverage counts are released. The original 120 different-seed stress batches now have an explicit robot-time/J table in `legacy_summary.csv`; they are not compared as matched nominal reliability data.

Matched mismatch mass coverage is 3/30 overall, entirely from early failed-grasp cases, and **0/27 among completions**. See Section 6.5 and `conditional_summary.csv`.

## R6 — Conditional intervals and failure dilution

**Addressed.** Table 2 uses jointly completed seed pairs. The analysis also supplies decision-reaching differences and separate method-only/passive-only failure counts. For nominal data those conditioning sets coincide. The exciting-path conditional excess is a practically constant 0.796 s; the previous unconditional 0.716 s included three zero-difference failures. Seed is the bootstrap unit (10,000 resamples). Per-seed effects are released in CSV and a strip plot. Conditional survivor comparisons are not used to hide probe-induced failures.

## R7 — Startup mechanism and penalty dominance

**Addressed.** Section 6.1 gives the noiseless initial acceleration expression and threshold m approximately 0.2598 kg. Completion counts and success-conditional time are primary. J is secondary, with penalties 1,5,10,30 s. Nominal low-yaw passive N=20 mean J changes from 32.234 to 90.234 s over those penalties, while paired active/passive differences remain unchanged only because failures coincide there. No industrial reliability inference is made. No new startup controller was fitted to remove held-out failures.

## R8 — Integral gain units

**Addressed without changing the controller.** Eq. (2) now uses k0*Omega²*eta, k0=6 s^-1. Clips are ±0.02 rad s or m s. The ideal scalar polynomial and Routh condition k0<2*omega are stated. Replacing the actual controller by 6*Omega³ would change the experiment and was not done. Saturated adaptive-loop stability is not claimed.

## R9 — Margin units, normalization and numerical effects

**Units and diagnostics addressed; a principled replacement scheduler is not claimed.** Mass and inertia coefficients are explicitly 0.16 s/kg and 0.16 s. Asymmetric normalization is disclosed as a retained engineering choice. Margin sensitivity is reported. The nominal prior margin is 0.1812 s; maximum logged post-grasp nominal margin is 0.1044 s. The screening cap binds in 0 of 74,580 nominal loaded-transfer schedule calls. N=20 passive mean rounding residuals are 15.18 ms exciting and 14.00 ms low yaw.

We do not replace the heuristic and then attribute its results to the original algorithm. A sensitivity-weighted optimal scheduler is outside this revision; conclusions remain conditional on the specified scheduler.

## R10 — Forecast definition, validation and allowance

**Addressed within the declared heuristic.** Both probe regressors, the canceling 0.05 s hold term, and recomputation of duration/screening at fixed mean are defined in Section 4.3. The 0.9 s allowance approximates actual 0.896 s elapsed time; comparing it with the net 0.796 s excess would conflate overhead and savings. It was fixed before the original held-out run and is varied explicitly in the extension; exact earlier tuning history is unavailable.

Figure 3 overlays realized, one-step and fixed-mean horizon uncertainty scales for 27 nominal low-yaw trajectories. Median fixed-mean predicted/realized ratios are 1.048 mass and 0.988 inertia, with mean absolute log ratios 0.048 and 0.042. Per-seed and probe predictions are included. These diagnostics do not establish a calibrated posterior or accurate decision costs under all mismatch/noise settings.

## R11 — Reproducibility and provenance

**Artifact and essential definitions addressed; historical tuning provenance only partially recoverable.** The paper states the probe profile, controller units, sampled failure scoring, Cartesian completion definition, task endpoints, segment-indexed RNG construction, development composition, environment and host. The full mass matrix remains in `docs/MODEL.md`, with payload entry into M stated in the paper. Original 120 development results and final frozen constants are preserved. No invented chronology of earlier tuning is supplied.

The delivery contains a reviewer-oriented anonymous archive with source and data. One command rebuilds revised tables/figures. No public URL was invented or public publication performed. Whether the venue accepts an uploaded supplement or requires an anonymous hosted URL remains a venue-specific step.

## R12 — Literature positioning

**Addressed.** Added verified references: Atkeson et al. (1986), Slotine and Li (1987), Swevers et al. (1997), Hjalmarsson (2005), Bombois et al. (2006). The manuscript explicitly acknowledges that cost-aware identification and learning without separate excitation are established. It distinguishes the simple integral estimator from classical adaptive-control laws and the fixed-mean batch forecast from Vantilborgh et al.'s trajectory-parametrized dual control. DOI/source details and verification scope are in `docs/LITERATURE_AUDIT.md`. This is a targeted literature audit, not exhaustive novelty certification.

## R13 — Physical mass/inertia combinations

**Addressed by a limited additional check.** Independent sampling is labeled synthetic. A matched N=20 check uses J=m*r_g², r_g uniform on [0.06,0.14] m. Non-oracle completion remains 27/30 and probe excess is 0.796 s exciting, 0.306 s low yaw. This is a plausibility-oriented sensitivity, not a fitted population distribution or payload geometry/clearance validation.

## R14 — Claims and computation wording

**Addressed.** The title, abstract and conclusion now describe regime dependence and decision regret. Equality with passive is explicitly explained by the same selected action. Planner cost remains a separate host-dependent diagnostic, not a meaningful throughput advantage or real-time guarantee. Failure modes of the proposed rule appear in the abstract and main results.

## R15 — Draft-process text

**Addressed.** Removed “Research draft,” “available to the researcher,” and submission-process commentary from the manuscript. Authorship is anonymous. The verified arXiv version is cited normally. Administrative status remains in the researcher README, not the scientific conclusions. The format is generic until a venue is selected.

## R16 — Figures

**Addressed.** Replaced the old figures with time decomposition, break-even/decision regret and forecast validation across 27 scenarios. Axes are readable and not clipped; uncertainty axes have multiple labeled logarithmic ticks. Per-seed effect and full sensitivity plots are also released. Overlapping action-equivalent methods are disclosed rather than interpreted as independent evidence.

## R17 — Tables and batch-size dependence

**Addressed.** Table 1 reports success-conditional robot times and completion counts. Table 2 reports paired means/intervals for all six nominal horizons and both families. Table 3 reports correct/beneficial/selected decisions and regret, including adverse cases. All methods and all settings remain in the machine-readable tables. Identical always-probe/ablation/threshold times are explained by identical physical actions.

## R18 — Uncertainty terminology and counts

**Addressed.** “Inflated variance” and “uncertainty scale” replace a calibrated posterior interpretation. Nominal coverage is 30/30 per method/family/horizon for both parameters; matched friction coverage and exact descriptive intervals are explicit. Counts recur across conditions and are not pooled as independent evidence. Neglected velocity-noise propagation through the friction integral, noisy regressors, endpoint sharing and mean projection are disclosed.

## R19 — Numerical verification detail

**Addressed for endpoint/state component reporting; no uncomputed bound is asserted.** The componentwise Christoffel errors now carry N m or N units. Independent integration errors are separated into rad, m, rad/s and m/s. Six plant-step-halving checks give endpoint Cartesian error below 7.8e-9 mm, yaw below 5.5e-10 degrees, and zero elapsed-time difference at the 2 ms resolution; endpoint state components are released. These are not full-trajectory supremum bounds. A separate quantitative bound on integral-estimation discretization bias is not established, and the manuscript does not claim one.

## R20 — Stress wording

**Addressed.** The original stress seeds differ, so their completion counts are not a matched nominal comparison. New matched tests support only the stated friction/coverage/time findings. The text no longer suggests the original comparison says anything about friction improving reliability.

## R21 — Analytical interpretation of probe value

**Addressed with a bounded diagnostic argument.** Section 7 states Delta_t_N = probe elapsed minus summed downstream savings. N approximately probe time / mean saving is explicitly only a constant-saving approximation; the measured nominal plateau invalidates naive linear extrapolation. No mathematical upper bound is claimed from the heuristic oracle gap.

## R22 — Scalar variance update

**Optional change not applied.** The original scalar P update is preserved for comparability. Its equivalent P*R/(R+Y²P) form could improve numerical expression, but no instability was observed in the integrity/numerical checks. Mean projection and inflated R already invalidate a strict posterior interpretation; that limitation is stated. We do not silently alter frozen computations for a cosmetic algebraic change.

## R23 — Anonymous artifact

**Local review artifact completed; external hosting not asserted.** `SCARA_Anonymous_Artifact.zip` inside the delivery contains the source/data/manuscript subset without personal author details or execution logs. It supports `python revision.py analyze`, `verify`, and `rerun`. A public or anonymous hosted URL must follow the eventual venue's policy; this revision does not invent one.

## Remaining limits and submission status

The computational revision, manuscript and response are complete. The work remains simulation-only, with a hand-set scheduler, limited scenario population, ten-seed sensitivity cells, reused seeds, no full interaction study and no published-method reimplementation. The original constant-selection chronology is only partly recoverable. The rule is demonstrably imperfect, and the title/claims reflect that.

A conference has not been selected or contacted. Before actual submission, the researcher must settle authors/affiliations and consent, venue fit, page limit/template, required disclosures, code license and artifact delivery method. These administrative choices are not represented by an invented author list, publication link or submission confirmation.
