# METHODOLOGY

## Pipeline
`Tide files → adapter (riskgraph/data/tide.py) → validation → account-day features (features/build.py) → temporal split → models → calibration (validation only) → capacity-constrained decision engine → explanation → analyst workflow → monitoring`. Offline stages write JSON artifacts under `artifacts/`; the API and UI only read them.

## Features (53, versioned `fv1`)
All are trailing windows over a dense [account × day] tensor; every feature has a registered definition (`FEATURES` in `features/build.py`).
* **T (25)** counts, amounts, max/mean/std of outgoing/incoming activity (1/7/30 days), transaction-type counts, night share, distinct currencies.
* **B (12)** new counterparties, distinct counterparties, repeat share, reciprocity, z-scores against the previous 30 days, velocity, in/out imbalance, top-counterparty share, active days.
* **G (8)** degree, 2-hop reach, neighbour degree/activity/hub share, triangles on a 7-day window graph (account-to-account edges only).
* **M (8)** directed 2/3/4-cycles, fan-in/fan-out bursts, pass-through ratio, near-10,000 amounts — defined a priori from Tide's documented typologies.
Thresholds that are assumptions (hub degree ≥ 20; near-threshold band 9,000–10,000) are named constants.

## Labels and leakage controls
Labels/scheme/family are returned only in a separate target table. Controls (all automated): future-perturbation invariance, label-independence, forbidden feature-name detector, split integrity, scaler fitted on training rows only, calibrator fitted on validation only, evidence limited to the decision timestamp.

## Split
Burn-in 30 d | train | validation | purge 14 d | test. Scheme-start rule: a positive case in a block whose schemes all started before the block is a *carry-over*; excluded from the primary view, kept in the sensitivity view. Training keeps all positives and 4 % of negatives; evaluation always uses the full population.

## Capacity and decision engine
`K_d = ceil(m × p_train × n_new_d)`. Day *d*: pool = new cases + backlog; REVIEW = top K_d by score; of the rest, AUTO-CLOSE if score ≤ τ_d else BACKLOG; backlog expires after 3 days. τ_d: **static** = α-quantile of validation positives (new-scheme view); **rolling** = α-quantile of all positives labelled by day *d* − 3; **conformal-corrected** = ⌊α(n+1)⌋-th smallest score in a 60-day window (no auto-close below 20 labelled positives). The engine reports realised miss, expired positives, backlog, weekly violation rate and per-family miss; it never asserts a guarantee.

## Statistics
Scheme-cluster bootstrap (500 resamples, resampling whole schemes) for recall, paired contrasts, relative loss and realised miss. With 8 (LI) and 15 (HI) independent schemes in the test stream all intervals are wide; results are effect sizes with uncertainty, not rankings.

## Explainability
LightGBM `pred_contrib` = exact TreeSHAP in log-odds (verified: contributions + base = raw margin, test `test_treeshap_contributions_sum_to_margin`). Reason codes only group features. Evidence = real transactions/edges at the decision timestamp. No LLM is used; the optional "AI Investigation Summary" was intentionally omitted (it would add risk without adding evidence).

## GNN decision
Not implemented: H1 shows no evidence that graph context beats behavioural features, the data volume per scheme is small, and only one CPU core was available. Adding a GNN would add complexity without evidence of benefit, so it is documented as a non-decision rather than implemented.
