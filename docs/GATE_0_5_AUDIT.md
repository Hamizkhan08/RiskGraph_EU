# GATE_0_5_AUDIT.md — Research verification and design challenge

```text
Gate 0.5 status:     PASS WITH REVISIONS  — design level only.
                     Data-level verification is OUTSTANDING. Implementation is NOT ready
                     (see IMPLEMENTATION_READINESS.md).
Date:                20 September 2026
Evidence reviewed:   RESEARCH_GAP.md, RESEARCH_DECISION.md (both re-audited);
                     IBM AMLworld paper + NeurIPS supplement/datasheet; IBM/AML-Data README;
                     Kaggle dataset description (via search-index text); CDLA-Sharing-1.0 full text;
                     SAML-D paper (ICEBE 2023), author GitHub repo, and one 2026 paper that uses it;
                     GARG-AML and Egressy et al. appendices (pattern coverage);
                     AMLA draft guidelines (read in Phase 0) + status checks; AI Act Omnibus status;
                     ~20 additional literature/regulatory searches (LIT_SEARCH_LOG.md).
Major changes from previous version:
  1. H2 as written is NOT testable on IBM data as specified (38–81% of laundering is untyped; typologies share motifs).
  2. Held-out unit changed from "typology" to "structural family".
  3. IBM Small (10 days) cannot support the temporal design → Medium becomes primary.
  4. Account-level bootstrap replaced by scheme-cluster resampling; "2 pp" effect threshold withdrawn.
  5. H3 re-specified: class-conditional conformal recall control; guarantee NOT assumed, measured.
  6. Capacity grid re-anchored to training-period prevalence.
  7. New leakage risk found: IBM data contain post-period transactions that are all laundering.
  8. HI-Small laundering-count discrepancy resolved at documentation level (5,177).
  9. Novelty classified Case B (partial overlap), not "gap confirmed".
```

Legend — **[V]** verified from a source I read · **[V-S]** verified from a secondary source · **[I]** inferred (arithmetic/assumption; must be checked) · **[U]** unverified.

---

## 1. Verdict

**What survived:** the decision-reliability framing (capacity → review → auto-close → backlog); the regulatory motivation (AMLA draft ¶43, 75–79, 84, 95); the synthetic-data premise; the idea of measuring the *realised* miss rate of an auto-closure rule, which is only possible because synthetic labels are complete.

**What failed or changed:** see the nine changes above.

**Why not FAIL:** a defensible question remains (typology-family shift × recall-calibrated auto-closure) and no prior work found in this session addresses it (`NOVELTY_AUDIT.md`).

**Why not a plain PASS:** no dataset file has been inspected; SAML-D's licence is unresolved; the literature protocol could only be run through a general web search engine, not through Semantic Scholar / Scopus / ACM / IEEE; and the number of independent evaluation windows cannot be fixed until the files are profiled.

---

## 2. What was and was not possible in this session

| Constraint | Consequence |
|---|---|
| No dataset files, no repository (only the two research docs existed) | Every dataset statement is **document-level**. The profiler (`ml/profiling/profile_dataset.py`) was written to settle them; it has only been tested on a synthetic fixture. |
| Kaggle not reachable from the working sandbox; the Kaggle page body does not render for the fetch tool | Kaggle licence field and the authors' reply about post-period transactions were **not read** |
| No direct Scopus / Semantic Scholar / ACM / IEEE / Google Scholar access | Literature check = structured web search; **incomplete relative to your protocol** — residual queries listed in `LIT_SEARCH_LOG.md` §3 |

---

## 3. IBM AMLworld — verification matrix

| Item | Finding | Source | Status |
|---|---|---|---|
| Exact name / URL | *IBM Transactions for Anti Money Laundering (AML)*, Kaggle owner `ealtman2019` | Kaggle; paper ref [50] | [V] name/URL; files not inspected |
| Official distribution | Kaggle is the "single source of distribution" and maintenance point. IBM/AML-Data (GitHub) describes the Kaggle data as *new and improved* and keeps older data on Box → **do not use the Box version** | NeurIPS datasheet; IBM/AML-Data README | [V] |
| Files | Per dataset: (A) transactions CSV, (B) text file listing laundering transactions that follow one of 8 AMLSim patterns. **Exact file names not confirmed** (third-party repos use `*_Trans.csv`) | Kaggle description | [V] structure / [U] names |
| Variants | HI/LI × Small/Medium/Large (6) | A1 | [V] |
| Transactions | HI-S 5,078,345 · LI-S 6,924,055 · HI-M 31,898,238 · LI-M 31,251,483 · HI-L 179,702,229 · LI-L 176,066,557 | BlazingAML Table 1 (edge counts) | [V-S] |
| Accounts | HI-S 515,088 · LI-S 705,907 · HI-M 2,077,023 · LI-M 2,032,095 · HI-L 2,116,168 · LI-L 2,070,980 | same | [V-S] |
| Date range (2022) | Small 1–10 Sep (10 d) · Medium 1–16 Sep (16 d) · Large 1 Aug–5 Nov (97 d). Described as the **"primary" period** | Kaggle description; supplement Table 4 | [V] |
| **Post-period transactions** | The Kaggle description states some transactions fall **after** the stated range and **all of them are laundering**; the authors' reply on "how to deal with it" was not read | Kaggle description (search-index text) | [V] existence / [U] guidance |
| Timestamp field | single `Timestamp` column; format assumed `YYYY/MM/DD HH:MM` | third-party listing | [U] — profiler reports parse failures |
| Currencies / formats | multiple currencies (list not obtained). Formats in LI-Large: cheque, credit card, ACH, cash, reinvestment, wire, bitcoin | A1 supplement Table 5 | [V] LI-L / [U] others |
| Label | `Is Laundering`, **transaction-level**, and **transitive** (tag propagates through all downstream transfers, including co-mingled funds) | A1 §3.4 | [V] |
| Pattern files | 8 patterns; **not all laundering follows one** | Kaggle description; supplement Table 8 | [V] |
| Duplicates / missing / malformed / stable IDs / schema drift across variants | Datasheet says no missing information and no known errors | supplement datasheet | [V] claim / [U] in file |

**Consequence of transitive labels:** a positive case means *"an account touched by a laundering-tagged flow"* — including receivers of disguised integration payments that may be ordinary-looking accounts. Wording must never say "criminal account".

---

## 4. The laundering-count discrepancy — resolution

| Evidence | HI-Small laundering count |
|---|---|
| NeurIPS supplement Table 4 (count row) | 3.6K |
| Same table, rate row: 1 per 981 → 5,078,345 / 981 | **5,177** (computed) |
| Kaggle description table | 5.1K |
| SAML-D paper, comparison table (`IT-AML`, HI-Small) | 5,177 (0.102%) |
| GARG-AML pattern table (3,209 pattern-classified + 1,968 not classified) | **5,177** (computed sum) |
| Third-party write-up: `value_counts(normalize)` = 0.101943% | 5,177 / 5,078,345 = 0.10194% ✔ |

**Explanation (documentation level, high confidence):** the "3.6K" in supplement Table 4's HI-Small cell is a **documentation error**. It is inconsistent with the paper's own rate and with four independent counts. It is *not* a different counting definition (all sources count transactions) and not a different dataset version. The value 3.6K equals the rate-implied count for **LI-Small** (6,924,055 / 1,942 ≈ 3,565), so a shifted cell is plausible but unproven.
**LI-Small remains unresolved:** documented 4.0K vs rate-implied 3,565.
**File-level counts still required** (transactions, positives, prevalence, accounts touching positives) — the profiler reports them; no number is to be adopted before then.

---

## 5. Pattern / typology coverage

**Documented coverage of laundering transactions by the 8 patterns** — much lower and much more variable than earlier notes implied:

| Dataset | Pattern-labelled | Untyped | Source |
|---|---:|---:|---|
| HI-Small | 3,209 (62.0%) | 1,968 (38.0%) | GARG-AML; Egressy App. I (38% "none") [V-S] |
| LI-Small | ≈29% | ≈71% | Egressy App. I [V-S] |
| LI-Large | 19,461 (19.3%) | 81,143 (80.7%) | supplement Table 8 [V] |

The untyped remainder is the *integration* stage, disguised as payroll, supplies etc. (supplement text). Multi-GNN recall on these transactions is close to 0% (Egressy App. I) — so they are also hard, untyped, and largely invisible to pattern features.

**Transactions per typology, HI-Small [V-S]:** fan-out 342 · fan-in 318 · gather-scatter 716 · scatter-gather 626 · cycle 287 · random 191 · bipartite 263 · stack 466.

**Independent scheme instances per typology — the number that governs statistical power:**
- LI-Large [V]: 259–298 per typology (2,228 total).
- HI-Small **[I]**: ≈ 29–51 per typology (≈ 325 total), obtained by dividing HI-Small pattern transactions by LI-Large transactions-per-instance. **Assumes the ratio transfers — must be verified from the file.**
- HI-Medium **[I]**: very roughly 200–340 per typology (×6.8 the laundering volume of HI-Small).

**Overlap:** LI-Large per-pattern transaction totals (Table 7) sum to 21,483 but unique pattern-labelled transactions are 19,461 (Table 8) → **2,022 (9.4%) difference**, consistent with transactions belonging to more than one pattern *or* double counting. To be resolved in the file.

**Required account-day table (to be filled by the profiler — not yet available):**

| Typology | Positive transactions | Positive account-days | Unique accounts | Coverage of laundering labels | Suitable for LOTO/LOFO? |
|---|---:|---:|---:|---:|---|
| *(8 rows)* | *[profiler]* | *[profiler]* | *[profiler]* | *[profiler]* | *decided by the rule below, not by transaction counts* |

**Suitability rule (pre-declared):** a family is usable as a held-out unit only if, **within the test block**, it has ≥ 30 independent scheme instances (start-time assigned) **and** ≥ 200 positive account-days **and** ≥ 50 unique positive accounts. Transaction counts are never used.

**Consequence:** on IBM, H2 must be defined on the **pattern-labelled layering subset only**, and the held-out unit must be a **structural family** (§11). Small datasets cannot meet the rule (≈30–50 instances per typology spread over 10 days).

---

## 6. Account-day unit → see `UNIT_OF_ANALYSIS.md`
Provisional decision: **account-day (Definition A) with trailing-window features**; account-3-day windows rejected on structural grounds.

---

## 7. Temporal feasibility

Spans are **documented, not observed** (profiler must confirm, and must cut at the primary-period end because of the post-period all-laundering transactions).

| Dataset | Days | Verdict |
|---|---:|---|
| HI/LI-Small | 10 | **Development only.** A burn-in + train + validation + purge + test layout leaves ≈2 test days, ≈65 test schemes **[I]** → ±12 pp at best. No multi-fold design. |
| HI/LI-Medium | 16 | **Primary.** Single confirmatory split; ≈690 test schemes **[I]** if scheme starts are roughly uniform → ≈±4 pp on scheme-level recall. |
| HI/LI-Large | 97 | Only if Medium proves too thin; use a temporal slice (~30–40 d ≈ 60–75M transactions); heavy on a laptop. |

```text
HI-Medium, days 1–16 (provisional, documented span)
Day:   1 2 | 3 4 5 6 7 8 9 | 10  | 11 | 12 13 14 15 16
       BURN|    TRAIN       | VAL | P  |      TEST
```
- **Burn-in (D1–2):** feature history only, not scored.
- **Purge (D11):** one day; additionally, **schemes whose first transaction is before the train/validation cut are excluded from later blocks' evaluation** (assignment by scheme start time) so continuing schemes do not contaminate.
- **Independent evaluation windows: effectively one test block.** Time is not a sampled unit; a second rolling-origin fold (test D14–16) is a **sensitivity check, not a replicate**. Claims about "temporal generalisation" are therefore limited to *this block*.
- Small: two-fold designs are dropped; the earlier "3 expanding folds" (`RESEARCH_DECISION.md` §5.4) is **withdrawn**.

---

## 8. SAML-D — verification

| Item | Finding | Source | Status |
|---|---|---|---|
| Official source | Kaggle `berkanoztas/synthetic-transaction-monitoring-dataset-aml`; author repo `BOztasUK/Anti_Money_Laundering_Transaction_Data_SAML-D` | repo README | [V] |
| Files | Repo lists only a README and a notebook; data on Kaggle | repo page | [V] |
| Size / prevalence | **Version drift.** Paper (ICEBE 2023): 9,411,384 tx, 11,658 suspicious (0.124%), 749,507 accounts. Current README: 9,504,852 tx, 0.1039%; README states it is *"an updated version compared to the one used in the publication"* | paper; repo README | [V] |
| Schema | 12 features: time, date, sender/receiver account, amount, payment type, sender/receiver bank location, payment/received currency, `Is Suspicious`, `Type` | paper; README | [V] names as published; [U] exact column names (a 2026 paper uses `Is_laundering`, `Laundering_type`) |
| Typology labels | 28 typologies (11 normal, 17 suspicious); 15 underlying graph structures — **several typologies share a structure**; suspicious accounts also send normal-typology traffic | paper | [V] |
| Counts by typology, date span | **Not published in the paper** | — | [U] — profiler |
| Account/entity info, graph reconstruction | Sender/receiver account IDs exist → graph and account-day construction feasible; no explicit bank IDs (bank *locations* only) | paper | [V] |
| Licence | **UNRESOLVED** — repo has no licence file; Kaggle licence field unread; the paper's own CC BY-NC applies to the *paper*, not the data | repo page; BURO record | [V] absence in repo |
| Redistribution / publication of derived results | Cannot be answered until the licence is read | — | UNRESOLVED |
| Prior use | A 2026 paper uses it with a chronological 70/15/15 split (so a usable time span exists) and reports test prevalence ≈0.119% vs 0.104% overall | arXiv 2608.15447 | [V-S] |

**Assessment:** SAML-D is scientifically attractive for H2 (every suspicious transaction carries a typology; 17 typologies; no pattern-file dependence) but **not usable for anything beyond local research until the licence is resolved**, and its version must be pinned by file hash. Its typologies are partly behavioural (structuring, smurfing, cash withdrawal, behaviour change), partly structural.
**Decision:** retained as a **candidate only**, gated by three checks (§17). Not introduced automatically.

---

## 9. Literature verification → `LIT_SEARCH_LOG.md`, `PRIOR_ART_MATRIX.md`, `NOVELTY_AUDIT.md`
Result: **Case B — partial overlap.** Capacity/top-K metrics and graph features for triage already exist; typology-held-out evaluation and risk-controlled auto-closure were **not found** in this incomplete search.

---

## 10. Research-question challenge (§12 of your brief)

**RQ tested (v1):** *Under a fixed daily review capacity, do graph-derived behavioural features improve the recall of laundering-related cases in the reviewed queue on temporally later data, and how reliable are capacity-based triage and auto-closure decisions when the test period contains laundering typologies absent from training?*

| # | Question | Verdict | Finding / change |
|---|---|---|---|
| 1 | Answerable? | Partly | (a) yes; (b) yes only for pattern-labelled layering and at family level |
| 2 | Dataset sufficient? | Medium: yes for H1/H3; H2 conditional | untyped share 38–81%; Small too short |
| 3 | Unit coherent? | Yes with caveats | `UNIT_OF_ANALYSIS.md` |
| 4 | IVs manipulable? | H1 yes; H2 yes (training-set composition); H3 yes (policy) | "typology-agnostic" is a *design intent*, not a manipulation check |
| 5 | DVs measurable? | Yes | realised miss rate needs full labels — satisfied by synthetic data |
| 6 | "Typology shift" reproducible? | **No, as defined** | replaced by *structural-family holdout* with an explicit assignment rule (§11) |
| 7 | Contamination? | **Yes** | untyped positives left in training; motif overlap (scatter-gather ⊃ fan-out+fan-in); schemes straddling the cut; shared accounts; post-period laundering tail |
| 8 | Capacity meaningful? | Only as an *experimental parameter* | anchored to prevalence (§13); never presented as bank capacity |
| 9 | Auto-closure formally specified? | **Not in v1** | §12 |
| 10 | Generator artifacts? | **Cannot be excluded** | Tide shows GFP gains vanish under another injection; IBM untyped laundering is nearly undetected |
| 11 | Defensible in a Master's dissertation? | Yes, as an evaluation-protocol study with honest scope | must accept possible null results |
| 12 | Completable by one student? | Yes only at Tier-1 scope | H3 and any second dataset are optional stretch |

### RQ — v2 (proposed; frozen only after profiling)
> *On time-ordered synthetic AML data, and assuming a fixed daily review capacity: (a) does adding generic graph-derived context to account-level behaviour raise the share of laundering-involved cases surfaced in the review queue; and (b) when the evaluation period contains laundering structural families absent from training, how far does the realised missed-laundering rate of a recall-calibrated auto-closure rule depart from its nominal tolerance, and does refreshing the calibration with delayed labels reduce that departure?*

---

## 11. Hypothesis audit

Common to all: unit = account-day case (§6); features from transactions with timestamp ≤ end of the case day; models = logistic regression (M1), gradient-boosted trees (M2/M3); temporal layout as §7; primary dataset IBM HI-Medium.

### H1 — value of graph context
| | |
|---|---|
| Independent | Feature set **T** (own activity) vs **T + G_ctx** (generic structural statistics: distinct counterparties, weighted degree, reciprocity, counterparty novelty, 2-hop reach). *Not* "typology-agnostic": degree statistics correlate with fan-in/fan-out by construction. Sensitivity to typology is **measured in H2, not assumed here.** |
| Dependent | Case-level recall@K in the test block at capacities in §13 |
| Training/validation/test | Train D3–9 · validation D10 (early stopping, calibration) · purge D11 · test D12–16 (§7). Same hyper-parameter budget for both feature sets |
| Statistics | Paired difference in recall@K at a **fixed score threshold** (negatives are abundant, so the threshold is stable); **positives resampled by scheme cluster**, paired across models; 5 training seeds reported separately |
| Min. sample | ≥ 100 independent test schemes (±8–10 pp resolution); ≥ 300 for ±5 pp |
| Success | Paired ΔRecall@K ≥ SESOI (set from pilot paired variance, **not 2 pp**; a priori resolution is ≈5–10 pp at 100–300 schemes) with 95% interval excluding 0 at the **single pre-declared primary capacity**; other capacities descriptive |
| Failure | Interval includes 0 or Δ < SESOI → reported as null |
| Confounders | Score calibration differences; feature count; account-degree heterogeneity; schemes continuing across the cut |
| Leakage risk | Trailing-window features must exclude labels and future days; post-period tail excluded; no raw timestamp features |

### H2 — structural-family shift
| | |
|---|---|
| Held-out unit | **Structural family**, not single typology. IBM proposal: F1 {fan-out, fan-in, scatter-gather, gather-scatter} (shared fan motifs) · F2 {cycle} · F3 {bipartite, stack} · F4 {random}. SAML-D families to be derived from its 15 published structures. *Rationale:* holding out scatter-gather while training on fan-out and fan-in tests composition, not novelty |
| Typology label of an account-day | Set of families of **pattern-labelled** transactions involving the account that day. Days with laundering involvement but **no pattern-labelled transaction = "untyped laundering": excluded from H2 training positives, H2 test positives *and* H2 negatives** (ignore class). Multi-family days are excluded from the held-out test unless every family is the held-out one |
| Independent | Feature type: **G_typ** (motif counts — cycles, fan, scatter-gather, biclique; GFP-style) vs **G_ctx** (H1). Held-out vs seen family |
| Dependent | Relative recall@K loss = (R_seen − R_held-out) / R_seen, per family |
| Procedure | Leave-one-family-out. Removed from training **and validation** positives: all cases of the family. "Seen" reference = same family in-distribution |
| Statistics | ≤ 4 folds ⇒ **no significance test across families**. Report per-family values with scheme-cluster intervals; summarise direction across families |
| Min. sample | Per §5 rule, evaluated **in the test block** |
| Success | G_typ loses more than G_ctx in ≥ 3 of 4 families **and** the mean paired difference's scheme-cluster interval excludes 0 |
| Failure | No consistent direction, or G_typ loses less → "typology-specific features generalise on this benchmark" |
| Contamination checks | (a) share of held-out positive **accounts** that also appear as training positives; report an *unseen-account* subset; (b) scheme start vs cut; (c) shared counterparties; (d) motif overlap between families |
| Limits | Typologies are simulated motifs; untyped 38–81% of laundering is outside H2 |

### H3 — auto-closure reliability
| | |
|---|---|
| Independent | Threshold policy: **P1** frozen empirical quantile from validation; **P2** empirical quantile refreshed daily from labels available after delay *L*; **P3** conformal-corrected quantile on a sliding window of recent labelled positives |
| Dependent | (i) realised miss rate; (ii) workload auto-closed; (iii) backlog volume/age; (iv) exceedance = share of evaluation days with daily miss > α + ε |
| Formal object | §12 |
| Statistics | Descriptive per day/fold; scheme-cluster intervals for the block-level miss rate |
| Min. sample | Finite-sample condition: a conformal recall threshold at tolerance α needs ≥ ⌈1/α⌉ − 1 independent calibration positives: **α=1% → 99, 5% → 19, 10% → 9, 20% → 4**. With ≈325 schemes (HI-Small **[I]**) α=1% is not credible; use α ∈ {5%, 10%, 20%} on Small, add 1% only on Medium+ |
| H3a | Same-regime test: P3's mean realised miss ≤ α + ε |
| H3b | Held-out family: P1 and P3 exceed α + ε; P2 reduces the exceedance |
| Not supported | Coverage holds under held-out families → positive robustness result |
| Assumption warning | **The formal guarantee does not apply.** It needs exchangeability between calibration and test positives; cases inside one scheme are dependent, time is ordered, and shift is imposed by design. H3 measures *how badly* the guarantee fails. It is never described as "guaranteed" |
| Label regime | Default: *oracle-delayed* (all cases labelled after *L* days). Sensitivity: *review-only labels* (selection bias — cf. PU learning) |

---

## 12. Auto-closure formalisation

For each day *d*: cases **C_d** = active account-days (new) ∪ **pending** cases carried from earlier days. Score *s(c)*; capacity *K_d*; threshold *τ_d* from policy.

```text
Rank C_d by s(c) (ties → deterministic hash)
   │
   ├─ top K_d ............................ REVIEW
   │
   └─ remaining C_d \ REVIEW
         ├─ s(c) ≤ τ_d ................... AUTO-CLOSE   ("safe" by policy)
         └─ s(c) >  τ_d ................... BACKLOG      (pending, age +1)
```
- **Mutually exclusive and exhaustive** by construction: REVIEW takes precedence; AUTO-CLOSE is evaluated only for non-reviewed cases; BACKLOG is the residual.
- Pending cases older than *M* days **expire** (unreviewed; a miss if positive). *M* is an assumption (default 3).
- τ_d = Q(𝓛_d, α, correction) — the α-quantile of **positive** scores in the labelled set 𝓛_d (cases from days ≤ d − L); "correction" = finite-sample conformal adjustment on/off.

**Definitions** (P = all positive cases in the evaluation block):
| Metric | Definition |
|---|---|
| Review recall | positives in REVIEW / P |
| **Realised miss rate** | positives in AUTO-CLOSE / P |
| Total-case recall | positives ever reviewed before expiry / P |
| Workload removed | \|AUTO-CLOSE\| / \|all cases\| |
| Backlog volume | pending cases at end of each day (and age distribution) |
| Expired positives | positives expired unreviewed / P |
| Scheme-level miss (secondary) | share of schemes with **no** case reviewed |

Case linking (reviewing one case resolves its scheme) is **not** modelled — conservative.

---

## 13. Capacity analysis

| Question | Answer |
|---|---|
| Are 0.1 / 0.5 / 1 % sensible? | **Cannot be judged before profiling.** At case prevalence *p*, a capacity r < p caps attainable recall at r/p; r ≫ p makes the queue trivially non-binding |
| Percentage or absolute? | **Both.** Primary: r = m × p̂_train with m ∈ {0.5, 1, 2, 5} (p̂_train = training-block prevalence of positive cases — legitimately known at deployment time, not leakage). Also report the implied absolute K/day and ρ = K / expected daily positives. Percent-of-volume grid kept for cross-dataset comparison |
| Real fact vs experimental parameter | **Experimental parameters** (assumptions): r, K, M, L, α, cost ratio. **Real-world facts we do not have:** any bank's capacity, review throughput, cost per alert (vendor figures of $30–80 appear in vendor material and are **not** used) |

Wording rule: "simulated review capacity K", never "investigator capacity".

---

## 14. Statistical design audit

| Issue | Finding | Decision |
|---|---|---|
| Unit of resampling | Cases within a scheme are dependent; accounts recur across schemes | **Cluster by scheme** (start-time assigned); check account overlap; account-level bootstrap **withdrawn** as primary |
| Time dependence | One confirmatory test block; days not independent | Time treated as fixed; folds descriptive; no pooled p-values across days |
| Repeated typology/family | ≤ 4 families ⇒ no inference across families | Descriptive across families; intervals within family |
| Seeds | Model-training variance ≠ data variance | Report seed spread separately from bootstrap intervals |
| Intervals | Percentile bootstrap of **paired** differences (same schemes, both models) | |
| Multiple testing | Many capacities × policies × slices | **One primary contrast per hypothesis, pre-declared;** everything else labelled exploratory |
| Effect size | v1's "2 pp" is below the resolution available at ≈100 schemes (±8–10 pp) | Withdrawn; SESOI from pilot paired variance, floor ≈ resolution |
| Ablations | T; T+G_ctx; T+G_typ; T+both; label-hiding stress test S1 | |
| Limits | Effective sample size = schemes, not cases: e.g. 1,000 positive cases in clusters of 5 with ICC 0.5 ≈ 333 effective | Report both raw and effective counts |

**Resolution table** (Wilson 95% half-width for a recall proportion, computed): 20 units ±17–20 pp · 50 ±11–13 pp · 100 ±8–10 pp · 300 ±4.5–5.6 pp · 1,000 ±2.5–3.1 pp.

---

## 15. Regulatory verification

| Item | Status as of 20 Sep 2026 | Source |
|---|---|---|
| AMLA ongoing-monitoring guidelines (Art. 26(5) AMLR) | **Still draft.** Published 3 Jun 2026; consultation closed 3 Sep 2026; final "expected Q4 2026". No final text found. A separate draft ITS on suspicion reporting closes for comments today (20 Sep) | AMLA consultation paper and page [V]; secondary items dated up to 5 days ago [V-S] |
| AMLR | Applies from 10 Jul 2027 (Reg. (EU) 2024/1624) | AMLA SPD; consistent secondary sources |
| AI Act Digital Omnibus | Reg. (EU) 2026/1744 of 8 Jul 2026, OJ 24 Jul 2026, in force 27 Jul 2026; Annex III high-risk obligations deferred to **2 Dec 2027**. Confirmed by ≥ 6 independent secondary sources including a public-body impact assessment; **OJ text itself not fetched** | [V-S] |
| AI Act classification of AML tools | **Not concluded.** Two summaries of the Commission's *draft* classification guidelines disagree; no legal conclusion is drawn | [V-S] |
| GDPR / model governance | Only what AMLA draft ¶10, ¶82, ¶88–95 say (data minimisation; synthetic/anonymised validation; model risk; drift). SR 11-7 / ECB guidance not reviewed | [V] |

**Wording:** "regulatory context considered during research design". Never "compliant".

---

## 16. Licence → `DATA_LICENCE_AUDIT.md`
IBM data: **CDLA-Sharing-1.0** per IBM's own repository; full text read; Kaggle page field not read. SAML-D: **UNRESOLVED**.

---

## 17. Dataset decision (§19 of your brief)

**Selected now: Option C — IBM only (Medium primary, Small for development), with explicit limitations.**
It is the only choice supported by verified facts today.

**Pre-declared upgrade to Option B (IBM + SAML-D)** — only if *all three* hold after checking:
1. SAML-D licence, read from the Kaggle page or obtained from the authors, permits research use and publication of aggregate results;
2. its date span supports the temporal layout (≥ 30 days) and the profiler shows every intended held-out family meets the §5 rule in the test block;
3. the dataset version is pinned by file hash and matches the counts the profiler reports.

*Scientific reason to upgrade:* IBM's typology labels cover 19–62% of laundering and its families overlap structurally, so H2 on IBM alone is exploratory; SAML-D's per-transaction labels can make it confirmatory. Having two datasets is **not** a reason.

**Pre-declared downgrade (Option D-lite):** if IBM-Medium *and* SAML-D both fail the §5 rule, H2 is dropped, the project becomes a capacity/auto-closure protocol study (H1 + H3 under *temporal* shift only), and the novelty claim is re-audited — it may then fall into Case C.

Option A alone is not selected: IBM Small→Medium is the development path, not a design.

---

## 18. Corrections to earlier documents (evidence trail kept)
| Earlier statement | Now |
|---|---|
| "HI-Small 3.6K vs ≈5.1K — unresolved" | 5,177 at documentation level; file count still required |
| "CDLA variant unconfirmed" | CDLA-Sharing-1.0 per IBM repo README; Kaggle field unread |
| "Pattern file covers a subset" | Quantified: 62% / ≈29% / 19% (HI-S / LI-S / LI-L) |
| "SAML-D 9,504,852 tx, 0.1039%" | Version-dependent: paper 9,411,384 / 0.124% |
| H1 "typology-agnostic" G_beh | Renamed G_ctx; agnosticism not assumed |
| H2 "leave-one-typology-out" | Leave-one-**family**-out on pattern-labelled subset |
| "cluster bootstrap over accounts"; "2 pp" | Scheme clusters; SESOI from pilot |
| "3 expanding folds" | Withdrawn (Small) / single block + sensitivity (Medium) |
| H3 "conformal risk control" | Class-conditional conformal recall control; guarantee measured, not claimed |
| Capacity 0.1/0.5/1% | Anchored to training prevalence |

---

## 19. Remaining risks
1. File-level facts unknown (spans, counts, tail, overlaps) — profiler.
2. Post-period all-laundering tail may already have inflated published results; must be excluded and quantified.
3. IBM untyped laundering (38–81%) is largely undetected by pattern features — H1 may look better on typed cases only; report typed and untyped separately.
4. H2 statistical power on IBM at family level.
5. SAML-D licence and version.
6. Incomplete literature protocol — Case B could become Case C.
7. Solo-build scope.
