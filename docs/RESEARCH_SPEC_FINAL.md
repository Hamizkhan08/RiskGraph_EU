# RESEARCH_SPEC_FINAL — RiskGraph EU

**Status:** FINAL for this build (supersedes `RESEARCH_SPEC_v1_PROVISIONAL.md`). Source of truth for the implementation in `riskgraph/`.
**Framing:** a research prototype for financial-crime *alert prioritisation and decision reliability under limited review capacity and constructed shift*, on public/synthetic transaction data. It makes no claim about real-world AML effectiveness, regulatory compliance, deployment readiness, or savings.

## 1. What changed from the provisional spec, and why

| Provisional (Gate 0.5) | Final | Reason (evidence) |
|---|---|---|
| IBM AMLworld (Medium) primary | **Tide generator, LI-like and HI-like conditions, generated locally** | Tide gives a 12-month span, explicit pattern metadata (every fraud transaction matched to exactly one pattern instance; verified), MIT generator. IBM's short spans and partial typology coverage (19–62 %) made the family experiment fragile. |
| Tide/AMLNet assumed to be usable as released | **Zenodo releases not used** | Zenodo is unreachable from the build environment; the Tide dataset licence and size claims could not be verified. Data is regenerated locally at reduced scale (1,500 individuals) and labelled as such everywhere. |
| AMLNet v2.0 as secondary validation | **Not used** | Record verified (1.09 M tx, 195 days, CC BY-NC 4.0) but typologies are laundering *stages*, no scheme IDs, a model-generated `fraud_probability` column (leakage risk), paper under review. Experimental adapter exists, untested on the real file. |
| Positives from schemes started before a block treated alike | **Scheme-start rule** | Scheme durations are long (see `DATA_CARD.md`), so a purge cannot separate blocks; carry-over positives are excluded from the primary ("strict") view and kept in an "all" sensitivity view. |
| H2 as a per-typology test | **Leave-one-family-out over Tide's 5 pattern types** | Family = generator `pattern_type`. Structural similarity between families is *not* assumed. |
| Capacity as a fixed share | **K/day = ceil(m × training prevalence × new cases)**, m ∈ {0.5, 1, 2, 5}; m = 1 primary | Anchoring capacity to a stated prevalence removes the circularity of choosing K from test data. |

## 2. Research question
Under a fixed daily review capacity, how reliably can transaction, behavioural and graph-based signals prioritise suspicious cases over time — and how does the reliability of calibrated auto-closure change under temporal, prevalence and unseen-typology-family shift?

Terminology (used consistently): **constructed distribution shift**, **structural-family holdout / typology-family shift**, **prevalence conditions (LI/HI)**. It is never called natural concept drift.

## 3. Hypotheses and pre-declared decision rules
Feature groups: **T** own activity · **B** behavioural history · **G** generic graph context · **M** typology/motif-aware (defined a priori from Tide's documented typologies).

* **H1** — adding G to T+B raises recall@K at fixed capacity. *Primary contrast:* M3 (T+B+G) − M2 (T+B), m = 1, new-scheme view, paired scheme-cluster bootstrap. *Rule:* "supported" only if the 95 % CI excludes 0 in the positive direction; otherwise "not supported".
* **H2** — M (typology-aware) features lose less recall than generic features when a family is held out. *Statistic:* relative recall loss on the held-out family; contrast M4 vs M3. *Rule:* reported per family with scheme counts; a family with < 5 independent schemes is flagged **underpowered**; no pooled claim without adequate schemes.
* **H3** — realised auto-close miss rate remains near its nominal tolerance α; rolling recalibration and conformal correction reduce violations. *Rule:* compare the CI of realised miss with α; **no coverage guarantee is asserted** (exchangeability is violated by scheme clustering, time ordering and the constructed shift).
* **Prevalence conditions:** LI and HI share one base population and differ only in fraud injection, so they are analysed **separately**, never as train/test of each other.

## 4. Unit of analysis and decision timestamp
Case = (account, day *d*). **Decision timestamp = end of day *d*.** Features use only transactions on or before day *d*. Enforced by construction (trailing windows over a dense account×day tensor) and by an automated future-perturbation test (`tests/test_leakage.py`), which is itself validated by a mutation test with a deliberately leaky builder.

## 5. Data
Primary: Tide LI-like (60 patterns) and HI-like (107 patterns), 1,500 individuals, 12 months, seed 42, generator commit recorded in every run manifest. Node attributes (`generated_nodes.csv`: `is_fraudulent`, `risk_score`, high-risk flags) are excluded because they are generator-side selection inputs. Transactions after the configured end date (all fraud) are excluded. Details: `DATA_CARD.md`.

## 6. Design constants (fixed before any model was fitted; `riskgraph/config.py`)
Seeds 11/23/37 · burn-in 30 days · train ends at 57.5 %, validation at 74 % of the period · 14-day purge before test · negatives kept for training only: 4 % · LightGBM hyper-parameters fixed, **no tuning** · α ∈ {5, 10, 20 %} (primary 10 %) · label delay 3 days · backlog expiry 3 days · conformal window 60 days · ≥ 20 calibration positives · 500 bootstrap resamples over schemes.

## 7. Models
M1 logistic regression (T+B) · M2 gradient boosting (T+B) · **M3 graph-enhanced gradient boosting (T+B+G), the main model** · M4 (T+B+G+M) · ablations A1 (T only) and A2 (T+B+G without transaction-type features). **No GNN:** not justified by the evidence (graph context did not help in H1) or the single-core compute; documented in `METHODOLOGY.md`.

## 8. Decision engine
Zones **REVIEW / AUTO-CLOSE / BACKLOG** (+ EXPIRED after 3 days), mutually exclusive. Policies: A static threshold, B rolling recalibration with delayed labels, C finite-sample-corrected sliding-window quantile ("conformal-corrected"), plus a no-auto-close baseline. Label regimes: *oracle-delayed* and *review-only* (selection bias).

## 9. Metrics
PR-AUC, recall@K, precision@K, lift@K, review workload, backlog size and age, auto-closed share, realised miss rate (auto-closed positives ÷ positives) **and** expired/unreviewed positive rate, Brier score against a prevalence-only baseline, ECE (interpreted with care at < 0.3 % prevalence), sensitivity across capacity and α. Accuracy is not reported; F1 is available only for comparability.

## 10. Deviations from pre-declaration (stated openly)
1. The strict/all evaluation views and the A2 (no-type) ablation were added after profiling showed long scheme durations and a near-giveaway transaction type — before any model was fitted.
2. The H2 evaluation window (days ≥ train end + purge) was chosen after counting schemes per family, to gain power; it includes the validation block, which is safe only because hyper-parameters are fixed and no model selection used it.
3. Scheme-cluster **confidence intervals for H3 were added after seeing the point estimates**; they widen, not change, the estimates.
4. The run manifests' timestamps reflect the last stage re-run (H3 was re-run to add intervals; H1/H2 outputs are unchanged).
5. AMLNet/TransXion/IBM were not used for results (see §1).

## 11. Explicit non-claims
No real-world effectiveness; no compliance with AMLD/AMLR/GDPR; no savings estimate; no determination that any account is involved in crime; no generalisation beyond this generator; LI/HI are not independent datasets.
