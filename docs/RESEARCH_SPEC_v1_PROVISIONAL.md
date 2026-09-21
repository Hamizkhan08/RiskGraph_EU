# RESEARCH_SPEC_v1_PROVISIONAL.md

```text
STATUS:  PROVISIONAL — NOT FROZEN.
         Renamed to RESEARCH_SPEC_v1.md only after the freeze procedure in
         IMPLEMENTATION_READINESS.md succeeds. Items marked [BIND] are set by the profiler
         through the pre-declared rules in §22 — never by looking at model results.
Date:    20 September 2026
Source:  docs/GATE_0_5_AUDIT.md (design), docs/UNIT_OF_ANALYSIS.md, docs/NOVELTY_AUDIT.md, docs/DATA_LICENCE_AUDIT.md
```
Why this file exists before the data: **decision rules written before seeing data are what keep the study defensible if results are negative.** It contains only rules and definitions, no results.

---

**1. Problem.** Under limited review capacity, which cases are examined, which are closed automatically, and how reliable is that closure when the future contains laundering structures unseen in training? Domain: AML transaction monitoring on **synthetic** data. Not a detection system, not a compliance tool.

**2. Gap (Case B, moderate confidence).** Capacity metrics and graph features exist; not found: held-out **structural-family** evaluation and a **realised miss rate** for recall-calibrated auto-closure under shift (`NOVELTY_AUDIT.md`).

**3. RQ (v2).** On time-ordered synthetic AML data and a fixed daily review capacity: (a) does generic graph context raise the share of laundering-involved cases surfaced in the review queue; (b) with held-out structural families in the test period, how far does the realised miss rate of a recall-calibrated auto-closure rule depart from its nominal tolerance, and does refreshing calibration with delayed labels reduce it?

**4. Hypotheses.** H1 (graph context), H2 (family shift), H3 (auto-closure reliability) exactly as specified in `GATE_0_5_AUDIT.md` §11. Each has a pre-declared failure condition; null results are reported.

**5. Unit.** Account-day case; label L1 = any involvement in a laundering-tagged transaction that day; sensitivity L2 (sender-side) if rule R4 fires. Wording: "risk signal", never "criminal account". Trailing-window features (≤ 3 days) attach to each case.

**6. Dataset.** Primary: IBM AMLworld **HI-Medium** (16 days, primary period only). Development: HI/LI-Small. LI-Medium for the HI/LI contrast. SAML-D: candidate, upgrade only via §22 R12. Files identified by name **and SHA-256** recorded by the profiler run. **[BIND]** exact counts.

**7. Licence.** IBM: CDLA-Sharing-1.0; raw data never in Git; only aggregates published; attribution string in README. SAML-D: UNRESOLVED (`DATA_LICENCE_AUDIT.md`).

**8. Typology definition.** Structural family (IBM proposal): F1_fan {fan-out, fan-in, scatter-gather, gather-scatter}, F2_cycle, F3_biclique {bipartite, stack}, F4_random. An account-day's family set = families of *pattern-labelled* transactions involving it that day. Laundering days without a pattern-labelled transaction = *untyped* → excluded from H2 training positives, test positives and negatives. Multi-family days excluded from held-out evaluation unless every family is the held-out one. **[BIND]** family list may merge if §22 R7 fires.

**9. Temporal split.** Provisional HI-Medium: burn-in D1–2 · train D3–9 · validation D10 · purge D11 · test D12–16; schemes assigned to a block by **first-transaction time**; schemes straddling a cut are excluded from later-block evaluation; post-period tail excluded. One confirmatory test block; a rolling-origin second block is a sensitivity check. **[BIND]** day indices after profiling.

**10. Capacity.** K_d = ⌈r × |C_d|⌉ with r = m × p̂_train, m ∈ {0.5, 1, 2, 5}; also report absolute K and ρ = K / expected daily positives; percent-of-volume grid for cross-dataset comparison. Experimental parameter only — never a claim about banks. One primary capacity is pre-declared (m = 1).

**11. Decision policy.** REVIEW → AUTO-CLOSE → BACKLOG with precedence and metrics of `GATE_0_5_AUDIT.md` §12. Policies P1 frozen empirical, P2 rolling empirical with delay L, P3 sliding-window conformal-corrected. α ∈ {5, 10, 20}%; 1% only if §22 R9 allows. M (expiry) = 3 days and L ∈ {1, 2} days are stated assumptions; label regime oracle-delayed with review-only sensitivity.

**12. Models.** M1 logistic regression (interpretable baseline); M2 gradient-boosted trees. Same hyper-parameter budget across feature sets; 5 seeds. Baselines: random; a simple volume/velocity rule. **Excluded:** GNNs, LLMs, deep models.

**13. Features.** **T** (own activity, trailing 1d/3d): counts/sums in and out, amount statistics, distinct counterparties, payment-format mix, currency mismatch, inter-transaction gap. **G_ctx** (generic structure, trailing 3d): weighted degree, reciprocity, counterparty novelty, 2-hop reach. **G_typ** (motif counts): high-degree fan indicators, short cycles, scatter-gather, biclique-like counts. No account or bank identifiers, no absolute time, no label-derived history.

**14. Leakage controls.** (i) Features from transactions with timestamp ≤ end of the case day only; (ii) post-period tail excluded and quantified; (iii) purge day + scheme-start assignment; (iv) held-out-family positives removed from training **and validation**; (v) thresholds and calibration only from labels available after delay L; (vi) burn-in for cold start; (vii) hyper-parameters tuned on validation only; test block touched once; (viii) unit tests on time-ordering for every feature function; (ix) no ID or time-index features; (x) untyped laundering never treated as negative in H2.

**15. Metrics.** Headline: recall@K (cases and, secondarily, schemes) at the pre-declared capacity. Also: precision@K, gain over random and over the rule baseline, realised miss rate, workload removed, backlog volume/age, expired positives, exceedance share. PR-AUC secondary. **Accuracy is never a headline metric.** Results always stratified typed vs untyped.

**16. Statistical analysis.** Scheme-cluster paired bootstrap at a fixed score threshold; seeds reported separately; one primary contrast per hypothesis; everything else exploratory; effect size and interval, not p-values; SESOI from pilot paired variance with floor ≈ resolution. No inference across ≤ 4 families. Raw and effective sample sizes reported.

**17. Ablations.** T; T+G_ctx; T+G_typ; T+both; label-hiding stress (review-only labels); untyped-excluded vs included; L1 vs L2 label; P1/P2/P3.

**18. Limitations (stated up front).** Synthetic data and one generator's typologies; simulated capacity; 38–81% of IBM laundering is untyped and largely undetected; conformal guarantee does not apply; single confirmatory time block; no entity-level view; no cost data; findings do not transfer to real institutions.

**19. Success criteria.** The project succeeds if it delivers a valid, reproducible protocol and honestly reported results **regardless of direction**. Hypothesis-level success/failure: `GATE_0_5_AUDIT.md` §11.

**20. Falsification criteria.** H1 falsified if the paired interval includes 0 or ΔRecall@K < SESOI at the primary capacity. H2 falsified if G_typ does not lose more than G_ctx in ≥ 3 of 4 families. H3a falsified if same-regime realised miss > α + ε; H3b falsified if held-out families do not exceed α + ε under P1/P3. A falsified hypothesis is reported as such and the hypothesis is **not** changed afterwards.

**21. Scope boundaries.**
- Tier 1 (must): profiler → H1 → H3 (same regime; frozen vs rolling) on HI-Medium.
- Tier 2 (only if §22 passes): H2 family holdout; SAML-D replication.
- Tier 3 (excluded until Tiers 1–2 are done): GNN, LLM, MLflow, richer UI.
- Frontend: a static results viewer **after** results exist; no live "detection" claims. No deployment before Tier 1 is complete.

---

## 22. Pre-declared decision rules (profiler → [BIND])

| Rule | Trigger (from profiler output) | Consequence |
|---|---|---|
| R1 Tail | any rows after the primary period | Exclude from cases; report count and laundering share; timestamps never used as features |
| R2 Power | HI-Medium test block < 200 positive account-days **or** < 100 scheme starts | Extend block (≤ 7 days); else move to a Large temporal slice; else H1/H3 descriptive only |
| R3 Unit | U5 > 50% schemes span > 1 day | Keep A; add 3-day label sensitivity |
| R4 Label | receiver-only > 50% of positive account-days | Add L2 sensitivity label |
| R5 Capacity | smallest r gives K_d < 10 cases/day | Drop that m; use absolute K ≥ 10 |
| R6 H2 on IBM | a family fails the §5 rule in the test block | Family excluded; if < 3 of 4 usable → H2 exploratory; if ≤ 1 usable → drop H2 unless R12 passes |
| R7 Overlap | > 10% of typed positives in > 1 family | Merge affected families or exclude multi-family days; report |
| R8 Account reuse | > 30% of held-out-family positive accounts also training positives | Primary H2 evaluation on the unseen-account subset |
| R9 α grid | independent calibration schemes < 99 | α ∈ {5, 10, 20}% only; add 1% at ≥ 99 (prefer ≥ 300) |
| R10 Untyped | untyped > 60% of laundering | Report typed/untyped separately in every H1/H3 table |
| R11 Parser | `W_PATTERN_MISMATCH` > 1% of pattern transactions | Fix parser/matching before any typology analysis |
| R12 SAML-D | licence permits research + aggregate publication; span ≥ 30 days; families meet §5 rule; version pinned by hash | Upgrade to Option B; otherwise remain Option C |
| R13 Novelty | residual search finds a study meeting `NOVELTY_AUDIT.md` kill criteria | Stop; re-audit before any code |
