# LIT_SEARCH_LOG.md — What was actually searched

Date: 20 September 2026 · Status: **INCOMPLETE relative to the Gate 0.5 protocol** (see §3)

## 0. Honest scope statement
- **Tool used:** a general web-search engine (returns ≤ 10 results per query; hits come from arXiv, ACM, Springer, IEEE landing pages, GitHub, vendor sites) plus direct fetches of specific documents.
- **Databases NOT queried directly:** Google Scholar, Semantic Scholar, ACM DL, IEEE Xplore, Scopus, ScienceDirect, SSRN. Where those sites appear below, the hit came through the general engine.
- "Results screened" = every result the engine returned for that query was read at least at title + excerpt level (**≤ 10**). "Relevant" = judged relevant to at least one component of RiskGraph EU. Counts are mine, not a database's.
- Because of this, **absence of a paper here is not evidence that it does not exist.** All novelty statements downstream are "not found in this search."

## 1. Literature queries run (all 2026-09-20)

Prefix **P** = Phase 0 (earlier in this project) · **G** = Gate 0.5 (this phase).

| ID | Database | Query (abridged) | Screened | Relevant | Key finding | Relation to RiskGraph EU |
|---|---|---|---:|---:|---|---|
| P1 | web | Realistic Synthetic Financial Transactions for AML Models, AMLworld, IBM | ≤10 | 1 | The dataset paper (Altman et al., NeurIPS 2023): synthetic, complete labels, transitive tags | Primary dataset source |
| P2 | web | IBM AML Kaggle HI/LI-Small licence CDLA illicit ratio | ≤10 | 3 | Size tables; SAML-D summary; independent review used HI-Small | Dataset facts |
| P3 | web | Elliptic2 subgraph dataset licence | ≤10 | 1 | 122K subgraphs, 49M nodes, ~26 GB, crypto | Rejected as core |
| P4 | web | Elliptic Data Set 203,769 transactions time steps licence | ≤10 | 2 | 49 time steps; dark-market shutdown at step 43; licence not found | Drift context only |
| P5 | web | AML alert prioritisation ML false-positive reduction investigator capacity precision@k | ≤10 | 2 | Vendors claim large FP cuts (unverified); real-bank triage paper exists | Motivation |
| P6 | arXiv (fetch, full read) | Deprez et al., network analytics for AML — review + benchmark | — | 1 | Gaps: prioritisation/learning-to-rank, cost-sensitivity, PU, dynamic, interpretability; synthetic data optimistic; window ≤ 2022 | Core prior art |
| P7 | web | Multi-GNN / provably powerful GNNs for directed multigraphs, AML | ≤10 | 3 | Multi-GNN, MEGA-GNN; F1-based, in-distribution | Model prior art |
| P8 | web | learning to rank AML alerts, limited capacity, cost-sensitive, graph features, temporal split | ≤10 | 4 | Real-bank triage with graph features (Feedzai authors); Tide generator: GFP gains vanish under another injection | Closest prior art |
| P9 | web | AML generalisation to unseen typologies, held-out pattern, IBM | ≤10 | 2 | Typology features studied in-distribution only | No LOTO found |
| P10 | web | unseen laundering typology, leave-one-typology-out, drift | ≤10 | 3 | Unsupervised typology discovery on Elliptic; TransXion benchmark | No LOTO found |
| P11 | web | conformal prediction / risk control, AML alert auto-closure, FNR | ≤10 | 2 | Conformal Risk Control (general); vendor doc on auto-closure | No AML closure study found |
| G1 | web | AML alert triage prioritisation recall@k limited analyst capacity graph features temporal 2025–26 | ≤10 | 3 | **Aug 2026 paper reports recall@top-K%, alerts/10k, chronological split on SAML-D (no graph features)**; Elliptic paper with leakage-safe graph features and PR-based triage; LLM triage framework | **Capacity/top-K metrics are NOT novel** |
| G2 | arXiv (fetch, partial) | Nahimana & Gaba, Rwandan mobile-money AML on SAML-D (arXiv 2608.15447) | — | 1 | Confirms SAML-D columns `Is_laundering`, `Laundering_type` (17 values), chronological 70/15/15, test prevalence ≈0.119%; LightGBM PR-AUC ≈0.047; graph methods deferred | SAML-D usability evidence; overlap on capacity metrics |
| G3 | web | conformal prediction AML / financial crime / fraud alerts FNR auto-close | ≤10 | 2 | **NCPNET**: non-exchangeable conformal prediction for temporal GNNs with an IBM-AML case study (prediction-set coverage, not a closure policy); vendor material | Partial overlap for H3 |
| G4 | web | ML distribution shift / unseen patterns / held-out pattern types on AMLworld | ≤10 | 4 | **Egressy App. I:** per-pattern recall reported in-distribution; untyped laundering ≈0% recall. **TU Delft thesis:** structural perturbations of laundering subgraphs on AMLworld degrade MEGA-GNN variants. GARG-AML pattern coverage tables | Partial overlap for H2; coverage data |
| G5 | web | "BEGIN LAUNDERING ATTEMPT" pattern-file format | ≤10 | 1 | Format text **not found**; only GARG-AML tables (irrelevant biomedical hits discarded) | Parser format stays [U] |
| G6 | web | IBM AML Kaggle: transactions after the date range "all laundering" | ≤10 | 0 papers | **Kaggle description states post-period transactions exist and are all laundering**; the authors' reply not retrieved | New leakage risk |

**Total:** 17 literature-oriented queries + 3 document fetches (Deprez full; Rwandan MM partial; NeurIPS supplement in §2).

## 2. Verification searches (data, licence, regulation)

| Date | Target | What was run | Outcome |
|---|---|---|---|
| 2026-09-20 | IBM licence | search; fetched IBM/AML-Data README result; fetched **CDLA-Sharing-1.0 full text** (SPDX) | CDLA-Sharing-1.0 per IBM repo; text read; Kaggle licence field unread |
| 2026-09-20 | IBM supplement | fetched NeurIPS supplement/datasheet | Table 4, 7, 8; datasheet; licence family |
| 2026-09-20 | SAML-D | search; fetched paper (BURO PDF); fetched author repo | Version drift; no licence file in repo; typology structure |
| 2026-09-20 | AMLA | search for final guidelines | Still draft; final expected Q4 2026 |
| 2026-09-20 | AI Act | 2 searches | Omnibus published/in force; AML classification unresolved |
| 2026-09-20 | Kaggle description | search (page does not render for fetch) | Date-range table, tail note |

## 3. Residual protocol — what YOU must still run (I could not)
Run in **Semantic Scholar**, **Google Scholar** and **Scopus/ACM/IEEE**, years 2019–2026, and append one row per query using the table format above (date · database · query · screened · relevant · finding · relation). Do not list irrelevant hits.

| Cluster | Queries from your protocol not run individually |
|---|---|
| Capacity / prioritisation | "AML learning to rank"; "AML top-k review"; "AML investigator workload"; "AML backlog"; "AML alert queue optimisation"; "transaction monitoring prioritisation" |
| Typology generalisation | "AML typology shift"; "AML out-of-distribution"; "AML graph feature robustness"; "AML synthetic typology robustness" |
| Auto-closure / risk control | "AML alert suppression"; "AML alert hibernation"; "AML false negative control"; "conformal prediction financial crime"; "AML risk-controlled decision" |
| Graph + decision | "graph AML investigation prioritisation"; "graph ML AML operational workload"; "network features triage" |
| Adjacent (not in your list, recommended) | "learning to defer" fraud/AML; "selective classification" fraud; "human–AI capacity" fraud review |

**Stop condition:** if any result reproduces H2 or H3 as specified in `GATE_0_5_AUDIT.md` §11, log it, update `PRIOR_ART_MATRIX.md`, and re-run the novelty classification before any code is written.

---

## Addendum 2026-09-21 — verification searches during the final build
| # | Query / source | Purpose | Outcome |
|---|---|---|---|
| A1 | Fetch `github.com/mntijn/Tide` (+ clone) | Generator licence, configs, output schema | MIT; 5 pattern types; README mentions `graph_LI.yaml` which is not in the repo; default `graph.yaml` ≈ LI, `graph_HI.yaml` ≈ HI |
| A2 | Fetch `zenodo.org/records/21237971` | Verify AMLNet v2.0 claims from a third-party summary | Claims confirmed (size, span, CC BY-NC 4.0); additional hazards found (stage-type typologies, `fraud_probability` column, paper under review) |
| A3 | Fetch `doi.org/10.5281/zenodo.18804069` | Tide dataset licence | Rate-limited; **unverified** |
| A4 | Web search: Render free web services, spin-down and ephemeral filesystem (2026) | Deployment facts for `DEPLOYMENT.md` | Render docs (updated Aug 2026): spin-down after 15 min, ≈ 1 min restart, ephemeral filesystem, 750 free hours/month |
| A5 | Web search: Vercel Node.js versions, Next.js 16, Hobby plan (2026) | Deployment facts | Next 16 needs Node ≥ 20.9; new projects default to latest LTS with a per-project override; Hobby plan reported as personal/non-commercial (third-party source — confirm on vercel.com) |
| A6 | Zenodo reachability from the sandbox (`curl`) | Whether released datasets can be downloaded | `host_not_allowed` — datasets inaccessible; local generation used instead |
