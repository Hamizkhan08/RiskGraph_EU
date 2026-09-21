# RESEARCH_GAP.md — Landscape, saturated ideas, candidate gaps

```text
Gate 0.5 status:     PASS WITH REVISIONS (design level only; data-level verification outstanding)
Date:                20 September 2026
Evidence reviewed:   see GATE_0_5_AUDIT.md (header) and LIT_SEARCH_LOG.md
Major changes from previous version:
  - HI-Small laundering count resolved at documentation level: 5,177 (not 3.6K).
  - IBM data licence: CDLA-Sharing-1.0 per IBM repository (text read); SAML-D licence UNRESOLVED.
  - Pattern coverage quantified: 62% (HI-Small), ~29% (LI-Small), 19% (LI-Large) of laundering transactions.
  - New leakage risk: IBM post-period transactions are all laundering (Kaggle description).
  - SAML-D size/prevalence is version-dependent (9,411,384 / 0.124% in the paper; 9,504,852 / 0.1039% now).
  - Novelty re-classified: Case B (partial overlap) - capacity metrics and graph features already published.
  - AMLA ongoing-monitoring guidelines confirmed still DRAFT as of 20 Sep 2026.
```
> **The text below is preserved unchanged as the evidence trail.** Where it conflicts with `GATE_0_5_AUDIT.md`, the audit governs. Corrected statements are listed in `GATE_0_5_AUDIT.md` §18. Do not implement from this file; the provisional specification is `RESEARCH_SPEC_v1_PROVISIONAL.md`.


| | |
|---|---|
| Project (working title) | RiskGraph EU |
| Phase | 0 — Research. **No implementation has started.** |
| Date | 20 September 2026 |
| Status | Draft for verification. §9 lists everything that has *not* been verified. |
| Companion document | `RESEARCH_DECISION.md` (final problem, methodology, self-critique) |

---

## 0. How this was produced, and its limits

- **Method:** about 35 targeted web searches, plus a full read of two primary documents: AMLA's draft ongoing-monitoring guidelines (3 June 2026) and the Deprez et al. review/benchmark (v4, July 2025). Everything else was read through abstracts and excerpts.
- **This is not a systematic review.** Novelty statements below mean *"not found in this pass"*, never *"does not exist"*. A documented literature protocol is scheduled as Gate 0.5 (see `RESEARCH_DECISION.md` §9).
- **Nothing was run.** No dataset was downloaded (Kaggle is not reachable from the working sandbox). No number here comes from our own experiments.
- **Evidence labels** used throughout:

| Label | Meaning |
|---|---|
| **[P]** | Primary source read: paper, regulator document, vendor's own page/repo (what the vendor *says*, not what is true) |
| **[S]** | Secondary: law-firm/consultancy note, blog, news |
| **[V]** | Vendor marketing claim. Recorded, **never used as fact** |
| **[U]** | Unverified / from prior knowledge. Must be checked before use |

Source IDs (A1, R1, V1…) resolve in §8.

---

## 1. Problem and regulatory context

### 1.1 The operational problem
- Transaction monitoring generates far more alerts than teams can review. Reported false-positive rates in the literature are "over 90%" (cited in A12) and 95–98% (cited in A4). **These are figures cited by other papers, not measured by us.** [P, second-hand]
- The dominant industry architecture is *rules generate alerts → an ML model scores/prioritises them → analysts review*. Feedzai describes exactly this on its own site [V2]; NICE Actimize describes predictive scoring that "hibernates" low-risk alerts [V1]. A4 reports the same pattern on real bank data [P].
- Vendor headline numbers (up to 40% fewer alerts "with 100% accuracy" [V1]; 70% fewer false alerts [V5]; 75%+ [V3]) are **undefined, unevidenced and not used** in this project.

### 1.2 What the EU supervisor now says (primary source)
AMLA's draft Guidelines under Art. 26(5) AMLR [R1] — published 3 June 2026, consultation closed 3 September 2026, final text expected Q4 2026. **Draft status: re-check before citing as final.**

| R1 ¶ | What it says (paraphrased) | Design implication for this project |
|---|---|---|
| 43 | Frameworks must be able to identify new ML/TF methods and typologies without undue delay | Evaluate on **typologies unseen in training** |
| 44 | Detect risk that only appears across transactions over time: linked/aggregated behaviour across accounts, network relationships, split or accumulated value | Motivates **behavioural and graph-derived features** |
| 75–76 | Monitoring outputs assessed without undue delay, **prioritised by risk**, explainable on request; mechanisms to address **accumulation of pending outputs** | Capacity and **backlog** are first-class evaluation concepts |
| 78–79 | Automated closure only for outputs that show no indicators of risk, never for higher-risk situations; effectiveness under human oversight incl. **periodic sampling and review of potentially missed cases** | Auto-closure needs a **measured miss rate** and a sampling-validation story |
| 82 | Testing/validation should, where appropriate, use **synthetic or anonymised data**; data minimisation | Supports the synthetic-data premise (not a compliance claim) |
| 84 | Effectiveness must not be judged solely by alert or reporting volumes | Never headline "alerts reduced by X%"; pair workload with detection outcomes |
| 85 | Validation of new methods should go beyond comparison with legacy outputs | Evaluate against held-out ground truth, not agreement with rules |
| 87, 89–90 | AI use is not itself evidence of effectiveness; model risk (inaccuracy, bias, robustness, transparency) must be considered; explainability **without requiring full technical interpretability** | Data-derived reason codes suffice; no "AI magic" claims |
| 95 | Tools must keep performance over time; degradation or **drift** must be identified | Monitoring module is justified |

---

## 2. Existing solutions (§3.1 of the brief)

| # | Approach | What it does | Technology / data | Strengths | Limitations | Status |
|---|---|---|---|---|---|---|
| 1 | **Rules + ML alert triage** (NICE Actimize [V1], Feedzai [V2], Hawk [V5], Tookitaki [V]) | Rule scenarios raise alerts; ML model ranks or suppresses them; case management | Proprietary bank data; behavioural profiling; vendors mention "white-box" explanations | Deployed at scale; fits investigator workflow | Claims unverifiable; no public benchmark; data not shareable | Commercial |
| 2 | **Entity resolution + network analytics** (Quantexa [V3, P]) | Resolves entities across sources, generates networks/context for monitoring and investigation | Proprietary; multi-source data | Context beyond single transactions; investigator-oriented | Vendor-reported effects only; no independent evaluation found | Commercial |
| 3 | **Featurespace** | Real-time AI transaction monitoring; acquired by Visa (completed 19 Dec 2024 [V4, P]) | Proprietary | Large deployment base (per Visa release) | Fraud-centred positioning; no capability claims verified here | Commercial |
| 4 | **Open-source monitoring engines** — Marble [V6], Tazama [V7] | Rule/typology engines, case management, ISO 20022 ingestion (Tazama) | Rules/typologies; APIs; self-hosted | Transparent, extensible, real workflow | Not research on ML triage; no public-data evaluation of models | Open source |
| 5 | **Simulators/datasets** — AMLSim [V8], AMLworld [A1], SAML-D [A7], Tide [A8], TransXion [A9] | Generate labelled synthetic transactions with injected laundering | Agent-based / typology-injection generators | Complete ground truth (real data has undetected laundering) | Detection bias: injected patterns can flatter pattern-aware models [A3, A8] | Academic / open |
| 6 | **GBDT + Graph Feature Preprocessor (GFP)** [A1] | Counts subgraph patterns (fan-in/out, cycles, scatter-gather…) as edge features for LightGBM/XGBoost | AMLworld HI/LI | Strong, interpretable; transaction-level F1 reported | Pattern-based; **gains not shown to hold when the generator/typologies change** (A8: GFP variants underperform base models on Tide) | Academic |
| 7 | **GNNs for directed multigraphs** — Multi-GNN [A2], MEGA-GNN [A10] | Message passing adapted (port numbering, ego IDs, reverse MP; two-stage edge aggregation) | AMLworld; a phishing dataset | Reported large minority-class F1 gains; theory for subgraph detection | F1-based; unstable under extreme imbalance in the independent benchmark A3 | Academic |
| 8 | **Alert triage with graph features on bank data** [A4] | ML model triages rule alerts; time-window dynamic graph; temporal 60/10/30 split; recall at fixed FPR | **Proprietary** real bank data | Closest to industrial reality; temporal split | **Not reproducible**; fixed-FPR metric, not capacity/backlog | Academic (industry data) |
| 9 | **Independent review + benchmark** [A3] | 97 papers reviewed; compares centrality, DeepWalk/node2vec, GCN/SAGE/GAT/GIN on Elliptic and IBM HI-Small | Public data | Neutral comparison; stresses AUC-PR | Literature window ends 2022; two datasets only | Academic |
| 10 | **Crypto subgraph / drift work** — Elliptic 1/2 [A5, A6], continual graph learning [A11] | Classify Bitcoin transactions/subgraphs; study shift (dark-market closure at time step 43) | Real, anonymised Bitcoin graphs | Real labels; natural shift event | Crypto ≠ bank AML; single shift event; licence unverified | Academic |
| 11 | **LLM reasoning over AML graphs** [A14] | Prompted LLMs reason over serialised IBM-AML subgraphs | IBM AML | Shows LLM narratives are already explored | Safety-sensitive; not evidence of detection value | Academic (preprint) |

**Not reviewed in this pass (no capability claims made):** SAS, FICO, Oracle, ComplyAdvantage, Napier.

### 2.1 What the independent benchmark (A3) establishes
- Over half of the reviewed literature relies on manual features or rules; only one paper reported AUC-PR; some reported accuracy alone; many top-cited papers lack baselines.
- Network features help **when combined with node features**. On IBM HI-Small (last 500k transactions) network structure alone was near random, GNNs were unstable under extreme imbalance, and the authors warn that **synthetic data can give overly optimistic results** (isolation forest worked on IBM but failed on real Elliptic data — criminals camouflage as "average").
- Stated gaps: benchmark standardisation, GNN interpretability, unsupervised methods, dynamic networks, **positive-unlabelled learning, learning-to-rank / limited-resource prioritisation, and cost-sensitive learning** (none of the covered papers used misclassification cost).
- Caveat: its literature window ends 2022.

---

## 3. Saturated ideas — rejected unless a specific gap justifies them (§3.2)

| Idea | Why it is rejected | Evidence |
|---|---|---|
| Plain RF/XGBoost transaction classifier on the Kaggle IBM data | Dozens of public repos; typically report accuracy/F1 on resampled data; A3 advises against accuracy | Public GitHub repos found in search [P]; A3 |
| Generic GNN on Elliptic (node classification) | Well-trodden since 2019; A3 finds GNN gains limited/unstable | A3, A6 |
| Simple anomaly detector (isolation forest etc.) | Fails on real data (AUC-ROC < 0.5 on Elliptic), "works" on IBM only because injected patterns are anomalous — a generator artifact | A3 |
| Graph visualisation dashboard | Open-source and commercial products exist; A3 notes visualisation papers rarely evaluate detection value | V6, V7, A3 |
| Generic SHAP dashboard | Existing examples on AMLSim; low differentiation (explanations remain *required*, not a contribution) | Public example [P] |
| "AI detects money laundering" | Unfalsifiable positioning; real labels are incomplete | A1, A3 |
| LLM "explains" AML alerts | Explored already [A14]; safety-sensitive; must never invent evidence | A14 |
| Generic credit-default prediction | Heavily saturated in public ML projects; no AML-style regulatory hook **[U — not researched in depth]** | — |

---

## 4. Public datasets — verification matrix

| Dataset | Size / structure | Labels | Time | Licence | Limits | Fits the selected question? |
|---|---|---|---|---|---|---|
| **IBM AMLworld** HI/LI × Small/Medium/Large [A1, D1] | HI-S 5M tx / 515K accts; LI-S 7M / 705K; HI-M 32M / 2.08M; LI-M 31M / 2.03M; HI-L 180M / 2.12M; LI-L 176M / 2.06M [A1 Table 4] | Transaction-level `Is Laundering`; **complete and transitive** (tag propagates downstream). Separate pattern file lists transactions in **8 AMLSim patterns — not all laundering follows one** [D1] | Small: 10 days; Medium: 16 days; Large: 97 days (2022) | "A Community Data License Agreement" per A1 supplement. **Exact variant not confirmed [U]**; CDLA-Sharing has share-alike terms — read before publishing derived data | Synthetic; injected patterns; short spans; multiple currencies (native amounts, not EUR). **Discrepancy:** A1 Table 4 lists 3.6K laundering tx for HI-Small, but the stated rate (1 per 981 × 5M) implies ≈5.1K; a third-party write-up lists 5.1K → **verify in our own profiling** | **Primary candidate** |
| **SAML-D** [A7] | 9,504,852 transactions; 12 features | 11 normal + 17 suspicious typologies; 0.1039% suspicious (A7 dataset summary) | **Span unverified [U]** | **Unverified [U]** | Newer generator, less external validation (IEEE ICEBE 2023 + PhD thesis); typology column must be confirmed in the file | **Conditional**: best fit for leave-typology-out if licence and span check out |
| **AMLSim** [V8] | Java generator; outputs accounts, transactions, alert lists (`alert_id`, `is_sar`) | Alert groups per pattern | Configurable | Repo licence to check [U] | Older; AMLworld was built to improve on it [A1] | Optional (native "alert" structure) |
| **Tide** (2026) [A8], **TransXion** (2026) [A9] | Customisable generators; profile-rich entities (TransXion) | Injected fraud/anomalies | — | Unverified [U] | Very new; not independently evaluated. Tide shows GFP gains disappear under a different injection mechanism | Watch-list only |
| **Elliptic 1** [A6] | 203,769 Bitcoin tx nodes; 234,355 edges; 166 anonymised features; 49 time steps | 4,545 illicit (2%), 42,019 licit, 157,205 unknown | 49 steps (~2 weeks); **dark-market shutdown at step 43 degrades all methods** [A3, A11] | **Not verified.** Third-party mirrors claim MIT but are re-uploads — do not trust [U] | Crypto, not bank AML; single shift event; anonymised features (no reason codes) | Not for core; optional drift sanity check |
| **Elliptic 2** [A5] | 122K labelled subgraphs; 49M nodes; 196M edges; ~26 GB [S] | Subgraph labels | — | [U] | Wrong domain, too large for a solo laptop | Rejected |
| Czech Financial Dataset, ICIJ Offshore Leaks [A3] | — | CFD has no AML labels; Offshore Leaks has no ground truth | — | — | Detection bias if patterns are injected; leaked-document ethics | Rejected |

**Conclusion:** IBM AMLworld (Small/Medium) is the only dataset that is credibly public, labelled, graph-structured, comparable to published work, and laptop-scale. It is **synthetic**, and every claim must say so.

---

## 5. EU context (§2 of the brief)

| Topic | Verified state as of 20 Sep 2026 | Source |
|---|---|---|
| AMLA | Established by Reg. (EU) 2024/1620; seat Frankfurt; operational since 1 Jul 2025; took over EBA's AML/CFT mandates 1 Jan 2026 | R2 (P, partly); several [S] |
| AMLR | Reg. (EU) 2024/1624 applies from **10 Jul 2027**; direct AMLA supervision of ~40 high-risk groups from 2028 (selection in 2027) | R2 [P]; [S] |
| Ongoing-monitoring guidelines | Draft published 3 Jun 2026; consultation closed 3 Sep 2026; final expected Q4 2026 | R1 [P] |
| EU AI Act timing | Digital Omnibus on AI, Reg. (EU) 2026/1744, published 24 Jul 2026, in force 27 Jul 2026; Annex III high-risk obligations deferred to **2 Dec 2027**; Art. 50 transparency unchanged | R4 [S, three consistent sources] — verify in the Official Journal |
| AI Act and AML systems | **Unresolved.** Annex III 5(b) (credit scoring) has a fraud-detection carve-out. Two summaries of the Commission's June 2026 *draft* classification guidelines disagree on whether AML systems share it | R5 [S] (McCann FitzGerald vs William Fry) |
| GDPR | AMLA draft stresses data minimisation and synthetic/anonymised testing data | R1 ¶10, ¶82 [P] |
| Model governance | AMLA draft ¶88–95 (model risk, oversight, drift). SR 11-7 / ECB guidance **not reviewed** | R1; [U] |

**Wording rules for this project:** "EU-oriented research prototype", "designed with European financial-services workflows in mind". Never "EU compliant", "GDPR compliant", "bank compliant". This is not legal advice; the AI Act classification question is for a lawyer if the system were ever deployed.

---

## 6. Candidate gaps (§3.3)

### G1 — Capacity-constrained triage evaluation on public data
| | |
|---|---|
| **Problem** | Models are ranked by F1/AUC, but teams review a *fixed number of cases per day*. What matters is how many true cases are inside the reviewed queue and what accumulates in the backlog. |
| **Evidence** | A3: threshold metrics and accuracy dominate; one paper used AUC-PR; learning-to-rank and cost-sensitivity absent (window ≤ 2022). R1 ¶75–76. A4 uses recall at fixed FPR on proprietary data. |
| **Existing solutions** | A4 (not reproducible); A1/A2 (minority-class F1); vendors (unverifiable). |
| **Missing capability** | A reproducible public-data protocol with capacity-based metrics and strict temporal ordering. |
| **Public data** | IBM AMLworld (complete labels). |
| **Feasibility** | High. |
| **Research potential** | **Moderate alone.** Without a sharper angle it collapses into "XGBoost + graph features" — a saturated idea (§3). |
| **Evaluation** | recall@K, precision@K, lift, backlog growth; paired bootstrap over days; expanding-window temporal folds. |
| **Portfolio value** | Clean and interview-friendly; modest novelty. |

### G2 — Typology-shift robustness of graph-derived features
| | |
|---|---|
| **Problem** | Pattern-aware features and GNNs are validated on the typologies present in training, yet supervisors expect detection of *new* typologies (R1 ¶43). |
| **Evidence** | A1: not all laundering follows the 8 patterns. A3: history-trained models degrade; synthetic detection bias. **A8: GFP-style features underperform base models when the generator's injection differs.** Elliptic step 43 is a real shift example [A3, A11]. |
| **Existing solutions** | A15 (unsupervised typology discovery on Elliptic with injected patterns); GFP/Multi-GNN evaluated in-distribution. **No leave-one-typology-out study found in this pass.** |
| **Missing capability** | Controlled measurement of what happens to *capacity metrics* when the test period contains typologies absent from training. |
| **Public data** | SAML-D (17 suspicious typologies, per-transaction — to verify); IBM pattern-labelled subset (8 patterns, partial coverage). |
| **Feasibility** | Moderate. Pattern-file parsing; small per-typology counts → wide intervals. |
| **Research potential** | **High for the effort.** The design is an *intervention on training-set composition*, so the result is interpretable either way. |
| **Evaluation** | Leave-one-typology-out (LOTO) recall@K on held-out vs seen typologies; feature-set × seen/unseen interaction. |
| **Portfolio value** | Strong: it directly answers "do your features just memorise the generator?" |
| **Caveat** | Typologies are simulated motifs. Conclusions concern the benchmark, not banks. |

### G3 — Safe auto-closure: controlling the missed-laundering rate under shift
| | |
|---|---|
| **Problem** | Vendors advertise auto-closing/hibernating low-risk alerts [V1]; the supervisor treats it cautiously and expects sampling-based validation (R1 ¶78–79). The trade-off *workload removed vs laundering missed* is rarely quantified with a stated risk bound. |
| **Evidence** | R1 ¶78–79. A12 reports a bank trialling auto-closure of lowest-scoring alerts with a separate review team. A13 gives distribution-free false-negative-rate control (including shift extensions). |
| **Existing solutions** | Thresholds chosen on validation recall/F1. **No conformal or risk-controlled auto-closure for AML found in this pass.** |
| **Missing capability** | Empirical evidence on whether a calibrated miss-rate bound survives temporal/typology shift, and how much workload it actually saves. |
| **Public data** | IBM / SAML-D. **Complete labels make the realised miss rate measurable — impossible on real data**, where missed laundering is unlabelled. |
| **Feasibility** | Moderate. Works on model scores; the maths is short; exchangeability assumptions must be discussed honestly. |
| **Research potential** | High; tied to current regulation. |
| **Evaluation** | Realised miss rate among auto-closed cases; frequency of bound violations across windows; workload removed at nominal tolerance; static vs rolling vs conformal calibration. |
| **Portfolio value** | Strong — but on short, stationary synthetic spans the bound may hold trivially. **Needs G2's shift to be informative.** |

### G4 — Label-delay-aware drift monitoring on real crypto data (Elliptic)
| | |
|---|---|
| **Problem** | Labels arrive late; monitoring must flag degradation without them (R1 ¶95). |
| **Evidence** | Time-step-43 collapse [A3, A11]. |
| **Existing solutions** | Continual-learning reviews and many Elliptic GNN papers. |
| **Missing capability** | Comparison of label-free drift signals against eventual performance loss. |
| **Public data** | Elliptic 1 — real, but crypto and **licence unresolved**. |
| **Feasibility** | High (small). |
| **Research potential** | **Moderate-to-low:** one shift event (n = 1) gives weak inference; heavily studied dataset. |
| **Evaluation** | Lead time of drift alarm vs performance drop. |
| **Portfolio value** | Moderate; crypto is off-message for an EU bank-workflow framing. |

### G5 — Finance-risk problems outside financial crime
| | |
|---|---|
| **Problem** | Credit risk, corporate distress, systemic risk. |
| **Evidence** | **Not researched in depth [U].** |
| **Data** | No public, labelled, licence-clear, EU-relevant dataset was identified in this pass. |
| **Decision** | Not pursued. Revisit only if Gate 0.5 shows the AML data are unusable. |

---

## 7. Selection (§3.4) — reasoning, not scores

**Selected: G2 and G3 measured inside G1's evaluation frame — "decision reliability of capacity-constrained AML triage under typology shift".**

1. **The regulatory hook is specific and current:** ¶43, ¶75–79, ¶84, ¶95 of the AMLA draft ask exactly for prioritisation, backlog control, bounded auto-closure and drift awareness — and ¶82 explicitly accepts synthetic data for validation.
2. **The literature points at it:** A3 lists prioritised predictions, cost-sensitivity, robustness and generalisation as open; A8 shows pattern-feature gains are generator-dependent; A1 admits partial pattern coverage.
3. **Public complete labels are uniquely suited:** they let us measure the *realised* miss rate of an auto-closure rule.
4. **It is feasible without GNNs or big infrastructure**: gradient-boosted trees on account-day features and a calibration layer.
5. **Why not the others:** G1 alone is a saturated model project; G2 alone has no decision layer; G3 alone risks a trivially-holding guarantee on stationary data; G4 rests on n = 1 and an unresolved licence.

**Not claimed:** that this is novel worldwide. Novelty is conditional on the Gate 0.5 literature protocol.

---

## 8. Research question and hypotheses — v0 (§3.5–3.6)

*These are the pre-critique versions. The frozen versions, with success/failure criteria, are in `RESEARCH_DECISION.md`.*

**RQ (v0):** Under a fixed daily review capacity, do graph-derived behavioural features improve laundering-case recall in the reviewed queue on temporally later data, and does a calibrated auto-closure rule keep its missed-laundering rate within a stated tolerance when the test period contains typologies absent from training?

| | Independent variable | Dependent variable | Evaluation |
|---|---|---|---|
| H1 | Feature set: transaction-only vs + graph-derived | recall@K at fixed capacity | Time-ordered folds; paired bootstrap over days |
| H2 | Typology status (seen vs held-out) × graph-feature type (typology-specific counts vs typology-agnostic) | Drop in recall@K | LOTO; interaction test |
| H3 | Calibration policy (static / rolling / conformal) | Realised miss rate among auto-closed; workload removed | Violation frequency across windows |

---

## 9. Not verified / open checks

1. Exact **CDLA variant** on the IBM Kaggle page (the page did not render for the fetch tool).
2. **SAML-D:** licence, date span, presence and coverage of the typology column.
3. **Elliptic 1** licence (mirrors claiming MIT are not authoritative).
4. **HI-Small laundering count** discrepancy (3.6K vs ≈5.1K) — resolve by profiling the file.
5. **Pattern-file coverage** per typology in HI/LI-Small and Medium.
6. **Post-2022 literature** on capacity-constrained AML triage, typology-shift robustness and conformal/risk-controlled auto-closure.
7. **AI Act classification of AML monitoring** — sources disagree; needs a legal reading.
8. **AMLA final guidelines** — draft only as of today.
9. Vendors not reviewed (SAS, FICO, Oracle, ComplyAdvantage, Napier); vendor claims not independently checked.
10. Whether Tide/TransXion data are downloadable and licensed.
11. Model-governance references (SR 11-7, ECB guidance).

---

## 10. Source register

**Academic / primary technical**
- A1 Altman et al., *Realistic Synthetic Financial Transactions for AML Models*, NeurIPS 2023 D&B — https://arxiv.org/abs/2306.16424
- A2 Egressy et al., *Provably Powerful GNNs for Directed Multigraphs*, AAAI 2024 — https://arxiv.org/abs/2306.11586
- A3 Deprez et al., *Network Analytics for AML — SLR and Experimental Evaluation*, arXiv 2405.19383 (v4, Jul 2025); code https://github.com/B-Deprez/AML_Network
- A4 Naser Eddin et al., *AML Alert Optimization Using ML with Graphs*, arXiv 2112.07508
- A5 Bellei et al., *The Shape of Money Laundering (Elliptic2)*, arXiv 2404.19109
- A6 Weber et al., *Anti-money laundering in Bitcoin*, arXiv 1908.02591 (cited via others)
- A7 Oztas et al., *SAML-D*, IEEE ICEBE 2023, DOI 10.1109/ICEBE59045.2023.00028; summary in arXiv 2404.14746
- A8 *Tide: A Customisable Dataset Generator for AML Research*, arXiv 2603.01863
- A9 *TransXion*, arXiv 2604.17420
- A10 *MEGA-GNN*, arXiv 2412.00241
- A11 *Advances in Continual Graph Learning for AML*, arXiv 2503.24259
- A12 *Machine Learning in Transaction Monitoring: The Prospect of xAI*, arXiv 2210.07648
- A13 Angelopoulos et al., *Conformal Risk Control*, arXiv 2208.02814
- A14 LLM reasoning over IBM AML graphs, arXiv 2507.14785
- A15 Unsupervised ensemble for new typologies (Elliptic), ResearchGate 395802232 (listing only)

**Regulatory**
- R1 AMLA, *Consultation Paper — Draft Guidelines on ongoing monitoring (Art. 26(5) AMLR)*, 3 Jun 2026 — https://www.amla.europa.eu/document/download/46b50078-08ed-4ab1-aea0-28b1a6085755_en?filename=Consultation+Paper+-+Article+26%285%29+AMLR.pdf
- R2 AMLA, *Single Programming Document 2026–2028* — https://www.amla.europa.eu/system/files/2026-02/AMLA%20SPD%202026-2028.pdf
- R3 Reg. (EU) 2024/1624 (AMLR) — http://data.europa.eu/eli/reg/2024/1624/oj; Reg. (EU) 2024/1620 (AMLAR) — http://data.europa.eu/eli/reg/2024/1620/oj
- R4 Digital Omnibus on AI, Reg. (EU) 2026/1744 — secondary summaries (Cloud Security Alliance note; Praxikon; Gibson Dunn)
- R5 Commission draft high-risk classification guidelines (Jun 2026) — secondary summaries (McCann FitzGerald; William Fry; DLA Piper)

**Vendors / open source / data pages**
- V1 NICE Actimize brochure — https://resources.niceactimize.com/wp-content/uploads/2024/11/aml-reducing-false-positives-in-transaction-monitoring-brochure.pdf
- V2 Feedzai AML — https://feedzai.com/use-cases/anti-money-laundering
- V3 Quantexa Contextual Monitoring brief — https://www.quantexa.com/assets/x/670c53045c/solution-brief-contextual-monitoring_fincrime-final.pdf
- V4 Visa, *Completes Acquisition of Featurespace* (19 Dec 2024) — https://corporate.visa.com/en/sites/visa-perspectives/newsroom/visa-completes-acquisition-featurespace.html
- V5 Hawk — https://hawk.ai/solutions/aml/transaction-monitoring
- V6 Marble — https://github.com/checkmarble/marble
- V7 Tazama — https://github.com/tazama-lf/docs
- V8 IBM AMLSim — https://github.com/IBM/AMLSim
- D1 Kaggle, *IBM Transactions for Anti Money Laundering (AML)* — https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
