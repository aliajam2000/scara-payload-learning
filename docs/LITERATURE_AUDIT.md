# Literature audit and claim boundaries

Checked 6 October 2026. This is a targeted primary-source search, not an exhaustive systematic review. Search expressions included combinations of SCARA, payload identification, dual control, batch, passive learning, time scaling, optimal experiment design and event-triggered learning. Recent versions were checked because the closest preprint changed substantially.

| Work | Verified source | Relevance and boundary |
|---|---|---|
| Vantilborgh, Sathyanarayan, Crevecoeur, Abraham, Lefebvre, *Learning On The Job: Zero-Shot Task Execution under Parametric Uncertainty via Trajectory-Parametrized Dual Control*, arXiv:2510.20483v2, 29 Sep 2026 | https://arxiv.org/html/2510.20483v2 | Full HTML inspected. Joint task execution and identification are established. Their reference is optimized through adaptive closed-loop dynamics; our scalar duration/covariance rollout does not reproduce that method. |
| Zhang, Zhou, Vasudevan, *Provably-Safe, Online System Identification*, RSS 2025 | https://www.roboticsproceedings.org/rss21/p121.html ; DOI 10.15607/RSS.2025.XXI.121 | Official abstract/BibTeX inspected. Safe exciting trajectories and rigorous parameter bounds already exist. Our approximate covariance and post-hoc sampled constraints provide no comparable guarantee. |
| Solowjow, Trimpe, *Event-triggered Learning*, Automatica 2020 | https://arxiv.org/abs/1904.03042 ; DOI 10.1016/j.automatica.2020.109009 | Author preprint abstract/metadata inspected. Triggering model learning is established, though their communication-based linear-Gaussian setting differs. |
| Feng, Jiang, *A Scheme for Simultaneous Optimal Tracking Control and Experiment Design*, IEEE Access 8, 25364–25371, 2020 | https://doi.org/10.1109/ACCESS.2020.2970593 ; author-uploaded full text: https://www.researchgate.net/publication/338926063_A_Scheme_for_Simultaneous_Optimal_Tracking_Control_and_Experiment_Design | Author-uploaded article inspected in the project literature review. Tracking and experiment-design tradeoffs are established; no claim to invent economic experiment design. |
| Moreno-Valenzuela, *Time-scaling of trajectories for point-to-point robotic tasks*, ISA Transactions 45(3), 407–418, 2006 | https://www.sciencedirect.com/science/article/pii/S0019057807602213 ; DOI 10.1016/S0019-0578(07)60221-3 | Publisher abstract inspected. Time scaling with model uncertainty/torque limits is established. Our grid screening is an explicit heuristic. |
| Lynch and Park, *Modern Robotics*, dynamics and trajectory-generation materials | https://modernrobotics.northwestern.edu/chapters/chapter8/ ; https://modernrobotics.northwestern.edu/chapters/chapter9/ | Official educational source for standard dynamics/reference construction. The synthetic SCARA constants are our benchmark choices. |

The arXiv v1 title *Dual Control Reference Generation for Optimal Pick-and-Place Execution under Payload Uncertainty* and v2 above are versions of one preprint, not two independent supporting papers.

## What this manuscript can claim

- A transparent batch-accounting benchmark that includes a learning-during-production comparator, common integral control, overhead, failed batches, uncertainty diagnostics and a deliberately flawed decision ablation.
- Within the specified synthetic distribution and one fixed probe, ignoring passive information acquisition causes unnecessary probes for N=20.
- The evaluated batch-aware rule avoids those probes, but does not improve simulated robot time over passive learning and incurs extra planner time.
- A clearly documented failure at initial load acquisition and a loss of mass-interval coverage under friction mismatch.

## What it cannot claim

- The first dual-control, active-identification, event-triggered-learning or time-scaling method.
- A globally optimal decision rule, a proof that probing never pays, or demonstrated superiority to published dual-control algorithms.
- A safety-certified controller, calibrated posterior under model mismatch, real-robot performance or broad robustness.
- Guaranteed conference acceptance or a definitive novelty search.

The present evidence best supports a bounded simulation/benchmark or negative-result contribution. A strong new-algorithm submission would require a stronger demonstrated distinction and additional validation, not stronger adjectives in its title.


## Post-review additions (verified 7 October 2026)

| Work | Primary source | Role / limit |
|---|---|---|
| Bombois et al., Automatica 42(10), 1651-1662 (2006) | https://doi.org/10.1016/j.automatica.2006.05.016 ; author manuscript https://perso.uclouvain.be/michel.gevers/PublisMig/LCID_final.pdf | Cost-aware identification, including information from ordinary operation. That principle is already known; our benchmark is a case study. Publisher confirms issue 10 (one institutional record incorrectly lists issue 5). |
| Hjalmarsson, Automatica 41(3), 393-438 (2005) | https://doi.org/10.1016/j.automatica.2004.11.021 | Application-oriented experiment design; metadata and publisher abstract checked. |
| Atkeson, An, Hollerbach, IJRR 5(3), 101-119 (1986) | https://doi.org/10.1177/027836498600500306 | Inertial identification from motion; publisher metadata/abstract checked. |
| Slotine and Li, IJRR 6(3), 49-59 (1987) | https://doi.org/10.1177/027836498700600303 | Online adaptive manipulation. Our estimator is not their algorithm and inherits no stability theorem. |
| Swevers et al., IEEE TRA 13(5), 730-740 (1997) | https://doi.org/10.1109/70.631234 | Optimized dedicated excitation; publisher abstract and author metadata checked. We use a fixed probe. |

The Vantilborgh arXiv entry does have v2 dated 29 September 2026; the review's uncertainty about the version is not evidence that the citation is wrong. The related-work text now contrasts the task-learning formulation explicitly and removes commentary about counting versions. The ignore-passive ablation is illustrative, without an unsupported claim of use in practice. The uncertainty-trigger comparator follows a broad trigger category but is not a replication of a published method. No exhaustive novelty certification is claimed.
