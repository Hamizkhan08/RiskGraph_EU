# RESEARCH_DECISION.md — Final problem, methodology and self-critique

```text
Gate 0.5 status:     PASS WITH REVISIONS (design level only; data-level verification outstanding)
Date:                20 September 2026
Evidence reviewed:   see GATE_0_5_AUDIT.md (header) and LIT_SEARCH_LOG.md
Major changes from previous version:
  - H2 re-specified: leave-one-STRUCTURAL-FAMILY-out on the pattern-labelled subset (not leave-one-typology-out).
  - "G_beh typology-agnostic" withdrawn -> G_ctx; agnosticism measured, not assumed.
  - Temporal design: Small (10 d) is development only; Medium primary; "3 expanding folds" withdrawn.
  - Bootstrap: scheme-cluster resampling replaces account-level bootstrap; "2 pp" effect threshold withdrawn.
  - H3: class-conditional conformal recall control; guarantee NOT assumed - measured.
  - Capacity grid re-anchored to training-period prevalence.
  - Formal REVIEW / AUTO-CLOSE / BACKLOG definition added (GATE_0_5_AUDIT.md section 12).
```
> **The text below is preserved unchanged as the evidence trail.** Where it conflicts with `GATE_0_5_AUDIT.md`, the audit governs. Corrected statements are listed in `GATE_0_5_AUDIT.md` §18. Do not implement from this file; the provisional specification is `RESEARCH_SPEC_v1_PROVISIONAL.md`.


| | |
|---|---|
| Project (working title) | RiskGraph EU |
| Phase | 0 — Research (decision record). **No code written.** |
| Date | 20 September 2026 |
| Version | v1 — becomes **frozen** only after Gate 0.5 (§9) passes |
| Evidence base | `RESEARCH_GAP.md` (source IDs A*, R*, V*, D* resolve there) |

---

## 1. Decision summary

| | |
|---|---|
| **Domain** | Financial crime / AML transaction monitoring — retained, but the *problem* was changed (see below) |
| **Final problem** | Not "detect laundering" (saturated). Instead: **how reliable are capacity-constrained triage decisions — who gets reviewed, what gets auto-closed — when the future contains laundering typologies the model never saw?** |
| **Gap** | Public-data AML work reports transaction-level F1/AUC on in-distribution splits. Nobody (in this pass) has measured capacity-based recall, backlog and the *realised miss rate of auto-closure* under typology shift, although the EU supervisor's draft guidelines explicitly ask for prioritisation, bounded auto-closure, new-typology detection and drift awareness (R1 ¶43, 75–79, 84, 95). |
| **Dataset** | IBM AMLworld HI/LI-Small (development) → Medium (confirmation). SAML-D as a *conditional* second generator. All **synthetic**. |
| **What is being built** | An evaluation protocol + empirical findings + a reference implementation and analyst-workflow viewer. **Not a new model.** |
| **Positioning** | "A research prototype for financial-risk alert prioritisation using public/synthetic data." |

---

## 2. Research question and hypotheses — v1

**RQ.** *Under a fixed daily review capacity, do graph-derived behavioural features improve the recall of laundering-related cases in the reviewed queue on temporally later data, and how reliable are capacity-based triage and auto-closure decisions — in particular the realised miss rate of a calibrated auto-closure rule — when the test period contains laundering typologies absent from training?*

**Unit of analysis ("case"):** one account on one calendar day. **Label:** the account is sender or receiver of at least one laundering-tagged transaction that day. *(Alternative: 3-day windows — decided after data profiling, before any modelling.)*

**Capacity:** review rate *r* = share of the day's cases that can be reviewed, swept over {0.1%, 0.5%, 1%} (**assumption**, configurable; synthetic data have no real staffing).

Numeric thresholds marked ◆ are **provisional and must be fixed from validation-fold variance before any test fold is touched.**

### H1 — Value of graph context under capacity
- **Independent:** feature set — **T** (an account's own activity only) vs **T + G_beh** (typology-agnostic graph context). Same model class (gradient-boosted trees), same tuning budget.
- **Dependent:** recall@K on later-in-time test days at each *r*.
- **Method:** 3 expanding-window folds, 5 seeds, cluster bootstrap over accounts (days are too few in the Small data to resample).
- **Supported if:** ΔRecall@K ≥ ◆2 percentage points **and** the 95% CI excludes 0 at ≥ 2 of 3 values of *r* in ≥ 2 of 3 folds.
- **Not supported if:** the CI includes 0 or the sign is negative → reported as a null result. *(A3 found that on IBM data only egonet-type features helped, so a null is plausible and informative.)*

### H2 — Typology shift
- **Independent:** test-case typology status (seen in training vs held out) × graph-feature type (**G_typ**: typology-specific motif counts — cycles, fan-in/out, scatter-gather, bipartite — vs **G_beh**: typology-agnostic behaviour).
- **Dependent:** relative recall@K loss = (R_seen − R_held-out) / R_seen.
- **Method:** leave-one-typology-out (LOTO) for typologies with ≥ ◆30 positive cases (else merge into families); bootstrap over typologies and accounts.
- **Supported if:** G_typ loses significantly more than G_beh (interaction CI excludes 0).
- **Not supported if:** no difference, or G_typ loses *less* — reported as "typology-specific features generalise on this benchmark".

### H3 — Auto-closure risk under shift
- **Independent:** calibration policy — (a) static threshold chosen on validation; (b) rolling recalibration using labels available after an assumed delay *L* (◆L ∈ {1, 2, 3} days); (c) conformal-risk-control threshold for false-negative rate (A13).
- **Dependent:** (i) realised miss rate = share of all laundering-positive cases that were auto-closed; (ii) workload auto-closed (%); (iii) share of evaluation windows where (i) exceeds the tolerance α ∈ {1%, 5%, 10%} (**assumption**, swept).
- **H3a (seen typologies):** policy (c) keeps mean realised miss ≤ α + ◆1 pp.
- **H3b (held-out typologies):** policies (a) and (c) exceed α + ◆1 pp; (b) reduces but does not remove the exceedance.
- **Not supported:** if coverage holds under held-out typologies, that is reported as a positive robustness finding. *(H3 deliberately predicts a failure so that it can be falsified.)*

**Optional stress test S1 (not a hypothesis):** randomly hide a share of laundering labels to mimic undetected laundering (the PU problem flagged in A3) and show how the *estimated* miss rate becomes biased.

---

## 3. Self-critique (§4 of the brief)

| # | Question | Honest answer | Design change made |
|---|---|---|---|
| 1 | Is this different from existing projects? | **Partly.** Graph features for AML (A1, A2), triage on real bank data (A4) and conformal risk control (A13) all exist separately. What I found *no trace of* in this pass is the **combination**: capacity metrics + typology-held-out evaluation + bounded auto-closure, on public data. Search was not systematic. | Contribution reframed as *evaluation protocol + findings*, **not a model**. Gate 0.5 adds a documented literature search. |
| 2 | Is the gap real? | Supported by three independent signals: A3's stated gaps, A8's generator-dependence result, R1's specific paragraphs. It could still shrink after a proper search. | Gap statement is worded "not found in this pass". |
| 3 | Can it be tested? | Yes — synthetic complete labels make realised miss rates measurable. But typologies are simulated motifs, so findings concern *the benchmark*. | Limitations §8 are part of every claim. |
| 4 | Is the dataset sufficient? | H1/H3: yes. H2: **conditional** — IBM's pattern file covers only a subset of laundering; per-typology counts may be small. Time spans are short (10/16 days), so "drift" here is *constructed typology shift*, not natural concept drift. | SAML-D as conditional second generator; explicit Gate 0.5 checks; never call the shift "natural drift". |
| 5 | Too ambitious? | **Yes, as originally specified.** The full brief (GNN, LLM, MLflow, Postgres, live inference, E2E, accessibility, performance, two deployments) is a multi-month solo build on top of the research itself. | Work split into tiers (§10); Tier 3 items are marked *not done* honestly rather than faked. |
| 6 | Is there a simpler, scientifically stronger design? | **Yes.** A simulated rule-alert layer would be written by me, so results would be circular. A GNN adds a confound. | Dropped the rule-alert simulation (evaluate the case queue directly); GNN becomes optional Model 4 only if H1 shows headroom; single unit of analysis; 3 feature sets × 3 policies factorial. |
| 7 | Technology only for CV keywords? | MLflow, live Postgres, GNN and LLM were at risk of being exactly that. | MLflow → versioned JSON/Parquet run records (MLflow only if it earns its place); Postgres only for analyst feedback; LLM last and optional (prior art exists: A14). |

---

## 4. Dataset decision

| Role | Dataset | Gate condition |
|---|---|---|
| Development | IBM AMLworld **HI-Small** (then LI-Small for the low-illicit-ratio check) | Profile file; resolve the 3.6K vs ≈5.1K laundering-count discrepancy; read licence text |
| Confirmation | IBM AMLworld **Medium** (DuckDB/Polars; avoid graph-breaking sampling) | Fits on a laptop after account-day aggregation |
| Typology experiments (primary) | Pattern-labelled subset of IBM (8 AMLSim patterns) | Coverage per pattern sufficient; else merge into families |
| Typology experiments (replication) | **SAML-D** (17 suspicious typologies, if verified) | Licence permits use; date span and typology column confirmed |
| Not used | Elliptic 1/2, Czech CFD, ICIJ Offshore Leaks | Licence unresolved / wrong domain / no ground truth |

**Licence handling:** the IBM data are released under "a Community Data License Agreement" (A1). The exact variant must be read from the Kaggle page. If it is the *Sharing* variant, derived **data** published in the repo/demo must respect share-alike terms — the safe default is to publish only aggregated results and code, plus a download script, never the raw data.

**Currencies:** the data contain several currencies. The UI shows native currency and amounts as recorded. Converting to EUR would require an invented FX assumption; if done, it will be a labelled, static, clearly-stated assumption.

---

## 5. Methodology (proposed; details go to `METHODOLOGY.md`)

**5.1 Pipeline.** raw → schema/uniqueness/null/value checks → account-day table → features (versioned) → time-ordered splits → scores → policies → metrics → artifacts. Every run records dataset version, feature version, model version, parameters, split boundaries, seed, metrics, artifact path.

**5.2 Feature families (all computed from transactions with timestamp ≤ end of the case day):**
- **T — own activity:** counts, in/out sums, mean/max amounts, in/out ratio, payment-format and currency mix, cross-bank share, hour-of-day dispersion, velocity relative to the account's own trailing baseline.
- **G_beh — typology-agnostic graph context:** distinct counterparties, weighted degree, counterparty novelty, reciprocity, ego-network density, counterparties' own activity statistics, 2-hop reach, trailing-window PageRank.
- **G_typ — typology-specific motifs:** time-respecting short cycles, fan-in/fan-out participation, scatter-gather/gather-scatter path counts, biclique/bipartite membership (GFP-style, A1).
- **The typology label is never a feature.** It is used only to construct splits and to slice results.

**5.3 Models.**
- **M1** logistic regression on T (interpretable baseline).
- **M2** gradient-boosted trees on T (traditional ML).
- **M3** gradient-boosted trees on T + G_beh, T + G_typ, and T + both (main model + ablation).
- **M4 (optional)** Multi-GNN-style model (A2) — only if H1 shows headroom and a fair comparison is feasible.

**5.4 Splits.** Expanding-window, time-ordered: train days → validation block → test block, with a one-day purge gap. No random splits, ever. LOTO for H2: held-out typologies are removed from training *and* validation positives but stay in the test period.

**5.5 Decision layer.** Score → rank → per-day top-K review (K from *r*) → below-threshold cases auto-closed under policy (a/b/c) → unreviewed remainder carries over as **backlog** with age. Cost per review and cost per miss are **configurable assumptions** with a swept ratio; they are never presented as bank costs.

**5.6 Explainability.** Tree-model attributions grouped into feature families as reason codes, plus an evidence view (focal account, counterparties, the actual transaction sequence and timestamps, matched motif). Every explanation is computed from model and data. **No LLM in the explanation path.**

**5.7 Statistics.** Cluster bootstrap over accounts; 5 seeds; effect sizes with intervals, not p-value theatre; multiple slices reported in full (no cherry-picking); ◆ thresholds fixed on validation only.

---

## 6. Evaluation strategy

| Metric | Why it matters here |
|---|---|
| **PR-AUC** | Threshold-free and appropriate at ≈0.1% prevalence (A3); ROC-AUC alone is misleading |
| **recall@K / precision@K** | The actual decision: what is inside the reviewed queue |
| **Workload / backlog size and age** | AMLA ¶76 concern; capacity is binding |
| **Realised miss rate of auto-closed cases** | The safety metric for H3 (measurable only because labels are complete) |
| **Brier score / calibration curve** | Auto-closure thresholds rely on calibrated scores |
| **False positives / false negatives (counts)** | Operational reading of the above |
| **F1** | Reported only for comparability with A1/A2, never as the headline |
| **Accuracy** | **Not reported as a performance metric** |

**Leakage checks (automated tests):** features use only timestamps ≤ case-day end; typology label absent from feature matrices; pattern-file membership never used as a feature; transitive laundering tags audited (a receiving account may be "positive" because of upstream flow — check this does not leak future information into features); train/validation/test account-day sets time-disjoint; scaler/encoder fit on training only.

**Results discipline:** every number shown anywhere comes from a recorded run; a `results/` manifest links each figure to a run ID; demo mode serves those precomputed results only.

---

## 7. Expected contribution (honest)

1. A reproducible public-data protocol for evaluating AML triage under **capacity** and **typology shift**.
2. Evidence, positive *or negative*, on whether graph-derived features survive unseen typologies.
3. An empirical look at the realised miss rate of auto-closure rules under shift — the quantity the supervisor asks banks to validate by sampling.
4. A reference implementation and analyst-workflow viewer for the above.

It will **not** show that any method works on real banks, quantify real savings, or establish regulatory compliance.

---

## 8. Limitations (must accompany any claim)

- **Synthetic data.** Generator design drives results (A3, A8). Findings describe the benchmark.
- **Constructed shift.** Spans of 10–16 days do not exhibit natural concept drift; typology shift is engineered by holding typologies out.
- **Simulated analyst feedback** in the UI; no real investigators; no real alert data.
- **Partial typology labels** in IBM; small per-typology counts widen intervals.
- **Unit-of-analysis choice** (account-day) is a modelling decision, not how any specific bank works.
- **Assumed costs, capacities, label delays and tolerances** are parameters, not measurements.
- **Legal:** nothing here is legal advice; AI Act classification of AML tools is unresolved in the sources I found (`RESEARCH_GAP.md` §5).

---

## 9. Scope, gates and stop rules

### 9.1 Tiers (engineering decision — the full brief is not one project)
| Tier | Contents | Status if unfinished |
|---|---|---|
| **1 — MVP** | Data pipeline + data card; evaluation harness with metric unit tests; M1–M3; H1 and H2; decision layer; analyst-workflow viewer (queue → case → explanation → network → simulated decision) on precomputed results; DEMO_MODE; core tests; Vercel deployment; docs | Required for "done" |
| **2** | H3 (conformal policy); monitoring page; FastAPI live scoring; Supabase persistence for analyst feedback; security review; backend deployment | Declared honestly if absent |
| **3** | M4 (GNN); LLM draft summaries; MLflow; full E2E/perf/accessibility audit | Marked "not done" — never faked |

### 9.2 Gates
| Gate | Content | Pass condition |
|---|---|---|
| **0.5 Verify** | Licence text (IBM, SAML-D); profile files; resolve laundering-count discrepancy; pattern-file coverage; SAML-D span & typology column; structured literature search (Semantic Scholar/Scopus/arXiv/ACM ICAIF, 2019–2026; terms: alert triage, prioritisation, learning-to-rank, conformal, auto-closure, typology shift/generalisation; log in `LIT_SEARCH_LOG.md`) | Licences permit use; gap survives search; v1 frozen |
| 1 Data | Pipeline, checks, `DATA_CARD.md` | Data tests green |
| 2 Harness | Metrics, splits, leakage tests, M1/M2 | Unit tests green **before** any model claim |
| 3 H1 | T vs T+G_beh | Result recorded either way |
| 4 H2 | LOTO | Result recorded either way |
| 5 H3 | Policies | Result recorded either way |
| 6 App | Viewer + DEMO_MODE | Manual + automated walkthrough |
| 7 Ship | Security, deploy, smoke test | Final audit |

### 9.3 Stop / pivot rules
- If graph features add nothing on H1 **and** H2 is uninformative → publish it as a rigorous negative result and make H3 + decision layer the headline.
- If licences block redistribution → publish code + download scripts only.
- If per-typology counts are too small → merge typologies into families; if still too small → drop H2 and say so.

---

## 10. Preliminary architecture (full version → `ARCHITECTURE.md`)

```
ml/ (offline Python) ──► artifacts/ (versioned Parquet + JSON: features, scores, metrics, explanations, evidence graphs)
                              │
                              ├──► apps/web (Next.js + TypeScript + Tailwind, Vercel)
                              │        DEMO_MODE (default): reads static, precomputed results — no backend required
                              │
                              └──► backend/ (FastAPI) — health, alerts, case, network, predict, explain, metrics, monitoring   [Tier 2]
                                        └──► Postgres (Supabase): analyst feedback + audit log only, synthetic IDs
```
- **Training is separate from inference** and never runs in Vercel functions.
- **Backend host is not chosen yet.** Current free-tier limits must be verified when `DEPLOYMENT.md` is written; no provider is assumed free.
- The UI labels **PUBLIC DATA / SYNTHETIC DATA / DEMO MODE / SIMULATED FEEDBACK** wherever relevant.

---

## 11. Risk register

| Risk | Mitigation |
|---|---|
| Synthetic-generator artifacts flatter results | Second generator (conditional); claims scoped to "benchmark"; report nulls |
| Novelty overstated | Gate 0.5 literature protocol; "not found in this pass" wording |
| Licence blocks use or redistribution | Read text at Gate 0.5; publish code + scripts, not data |
| Over-scoping | Tiers, gates, stop rules |
| Small per-typology counts | Families, intervals, drop H2 if necessary |
| Label semantics (transitive tags) | Audit; leakage tests |
| Compute (Medium = ~32M rows) | Account-day aggregation with DuckDB/Polars; Small first |
| Regulatory misstatement | Wording rules; cite drafts as drafts; no compliance claims |
| Vendor claims creeping in as facts | Recorded as [V] only, never used in results |
| Sandbox cannot reach Kaggle | You download the files locally (§12) |

---

## 12. Immediate next actions

1. **You:** download **HI-Small** (+ its pattern file) and, if possible, **SAML-D** from Kaggle, and paste the exact licence text shown on each page.
2. **Me:** write the profiling script (schema, nulls, duplicates, time span, laundering counts, pattern coverage) and the Gate 0.5 literature-search log template.
3. **Me:** after profiling, freeze v1 of this document and write `DATA_CARD.md`.
4. **You:** tell me your deadline (thesis/interview) so the tier boundaries in §9.1 can be fixed.
