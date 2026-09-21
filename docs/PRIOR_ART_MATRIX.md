# PRIOR_ART_MATRIX.md — Which components already exist?

Date: 20 September 2026 · Built from `LIT_SEARCH_LOG.md` (**incomplete search** — see its §0 and §3)

**Legend:** ✔ present in the text I read · ◐ partial / indirect · ✘ absent in the text I read · ? not verifiable from what I read.
**Read depth:** FULL · EXCERPT (substantial part) · ABSTRACT (abstract or snippet only). A ✘ from an ABSTRACT-depth row means *"not mentioned in the abstract"*, not *"absent from the paper"*.

The key question is not *"has anyone built RiskGraph EU?"* but *"which components exist and what evaluation protocol is underexplored?"*

| Work | Data | Unit | Graph features | Capacity | Top-K | Typology shift | Auto-closure | Risk control | Temporal validation | Public data | Read depth |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Naser Eddin et al. 2021 (Feedzai authors), AML alert optimisation | proprietary bank alerts | account/entity | ✔ dynamic-graph features | ◐ recall@20%FPR; suppression / prioritisation / hybrid mentioned | ✘ | ✘ | ◐ suppression framing, not evaluated as a policy | ✘ fixed-FPR point, no guarantee | ✔ 60/10/30 | ✘ | EXCERPT |
| Altman et al. 2023, AMLworld + GFP + GNNs | IBM synthetic | transaction | ✔ | ✘ | ✘ (F1, PR curves) | ✘ in-distribution | ✘ | ✘ | ✔ time-ordered features | ✔ | supplement FULL |
| Egressy et al. 2024, Multi-GNN | IBM synthetic (+ phishing) | transaction | ✔ | ✘ | ✘ | ◐ **per-pattern recall, in-distribution**; untyped laundering ≈ 0% | ✘ | ✘ | ? | ✔ | ABSTRACT + appendix |
| Deprez et al. 2025, review + benchmark | IBM HI-Small (last 500k) + Elliptic | transaction/node | ✔ | ◐ top 0.1/1/10% thresholds | ◐ precision/recall/F1 at top-x% | ✘ | ✘ | ✘ | ✔ 60/20/20 by time | ✔ | FULL |
| **Nahimana & Gaba 2026**, Rwandan mobile-money AML | SAML-D | transaction | ✘ (graph deferred) | ✔ alert budget, alerts/10k | ✔ recall@top-K% | ✘ | ✘ (risk bands) | ✘ (~90%-precision threshold, no guarantee) | ✔ chronological 70/15/15 | ✔ | EXCERPT |
| Khaleghpour & McKinney 2026, leakage-safe graph features | Elliptic | transaction | ✔ causal structural | ◐ alert-budget PR analysis | ◐ | ✘ | ✘ | ✘ (calibration only) | ✔ time-respecting | ✔ (licence unresolved) | EXCERPT |
| **NCPNET 2025**, non-exchangeable conformal prediction for temporal GNNs | temporal graphs + IBM-AML case study | node? | ✔ | ✘ | ✘ | ◐ OOD motivation only | ✘ | ◐ **conformal coverage, non-exchangeable** — not an FNR/closure policy | ✔ | ✔ | EXCERPT |
| Angelopoulos et al., Conformal Risk Control | CV / NLP | — | ✘ | ✘ | ✘ | ✘ | ✘ | ✔ **FNR control; shift extensions** (general method, not AML) | ✘ | ✔ | ABSTRACT |
| TU Delft thesis (title not retrieved), evasion perturbations | AMLworld | subgraph / transaction | ✔ MEGA-GNN variants | ✘ | ✘ | ◐ **parameterised structural perturbations** (intermediary injection, merge, split) degrade models | ✘ | ✘ | ? | ✔ | ABSTRACT |
| Tide 2026, dataset generator | Tide synthetic | ? | ✔ | ◐ notes capacity-driven thresholds; reports Youden | ✘ | ◐ **GFP gains vanish under a different injection mechanism** | ✘ | ✘ | ✔ leakage-safe | ✔ (generator) | EXCERPT |
| Continual graph learning review 2025 | IBM HI-Small + Elliptic | node | ✔ | ✘ | ✘ | ◐ Elliptic step-43 shift | ✘ | ✘ | ✔ | ✔ | EXCERPT |
| ExSTraQt 2026 | ? | transaction | ✔ quasi-temporal graph | ◐ analyst-workload motivation | ? | ? | ? | ? | ? | ? | EXCERPT |
| Oztas et al. 2023, SAML-D data paper | SAML-D | transaction | ✘ | ✘ | ✘ | ✘ (labels exist) | ✘ | ✘ | ✘ stratified split | ✔ (licence unresolved) | FULL |
| Vendor architectures (NICE Actimize, Feedzai) **[V]** | proprietary | alert | ◐ | ✔ prioritisation | ? | ✘ | ✔ "hibernate" (vendor-stated) | ✘ claims undefined | ? | ✘ | brochures — *not evidence* |
| **RiskGraph EU (planned)** | IBM Medium; SAML-D conditional | account-day | ✔ G_ctx, G_typ | ✔ experimental capacity | ✔ | ✔ **family holdout** | ✔ formal zones | ◐ conformal recall control, **measured, not assumed** | ✔ single block + sensitivity | ✔ | — |

---

## Component-by-component status

| Component | Exists already? | Where | Implication |
|---|---|---|---|
| Capacity-style metrics (recall@K%, alerts per volume) on public data with chronological split | **Yes** | Nahimana & Gaba 2026 (SAML-D); partial in Deprez | Not a contribution |
| Graph-derived features for AML triage | **Yes** | Naser Eddin (proprietary); GFP/Multi-GNN | H1 is a replication/extension, expected small effect |
| Per-pattern (typology) recall, in-distribution | **Yes** | Egressy appendix | Not novel |
| Robustness to *changed* laundering structure | **Partly** | TU Delft perturbation thesis (AMLworld); Tide (generator dependence) | H2 must be framed as **held-out families**, distinct from perturbation |
| Conformal prediction on temporal AML graphs | **Partly** | NCPNET | Coverage of predictions, not closure policy or capacity |
| Recall-controlled **auto-closure** evaluated with a **realised miss rate** under shift on public data | **Not found** | — | Candidate contribution (H3) |
| **Held-out structural-family** evaluation of capacity metrics | **Not found** | — | Candidate contribution (H2) |
| Combination of the three above | **Not found** | — | Candidate contribution; moderate confidence only |

## Closest neighbours (must be cited and differentiated)
1. **Nahimana & Gaba 2026** — same dataset family, capacity metrics, chronological split → RiskGraph EU adds graph context, family holdout and auto-closure risk.
2. **Naser Eddin et al. 2021** — real bank alerts, graph features, suppression framing → RiskGraph EU is reproducible on public data and measures realised miss rate under shift.
3. **NCPNET 2025** and **Conformal Risk Control** — conformal/risk-control machinery → RiskGraph EU uses it as a *policy* and tests its assumptions on clustered, ordered data.
4. **TU Delft perturbation thesis** and **Tide** — generator dependence / structural change → RiskGraph EU holds out whole families rather than perturbing subgraphs.
