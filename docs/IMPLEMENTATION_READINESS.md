# IMPLEMENTATION_READINESS.md

Date: 20 September 2026 · Rule: **implementation (any modelling code) is allowed only when every critical item is YES.**

```text
Dataset verified:                  NO   — documentation-level only; no file inspected
Licence verified:                  NO   — IBM: CDLA-Sharing-1.0, text read, Kaggle field unread; SAML-D: UNRESOLVED
Schema verified:                   NO   — header/format assumed; profiler stops if wrong
Temporal span verified:            NO   — documented spans only (10/16/97 days); tail not measured
Typology coverage verified:        NO   — documented coverage 62% / ~29% / 19%; account-day table not produced
Unit of analysis frozen:           NO   — provisional Definition A; checks U1–U9 pending
Leakage rules frozen:              NO   — draft rules written; tail rule awaits profiler
Temporal split frozen:             NO   — provisional Medium layout; final after day counts
Capacity definition frozen:        NO   — rule frozen (m × training prevalence); numbers pending prevalence
Auto-close definition frozen:      YES  — zones, precedence, metrics fixed (GATE_0_5_AUDIT §12); α, M, L bound later
Research question frozen:          NO   — v2 proposed
Hypotheses frozen:                 NO   — v2 proposed; H2 depends on profiler
Literature gap audited:            NO   — structured web search only; residual protocol outstanding
Regulatory references verified:    YES  — AMLA still draft; AI Act Omnibus verified; no compliance/classification claims
Implementation ready:              NO
```

## What is *not* blocked
- Running the **profiling instrument** on the real files (it is a verification tool, contains no modelling). It exists now: `ml/profiling/profile_dataset.py`.
- Writing documentation, running the residual literature search, resolving the licences.

## Blockers and what unblocks each

| Blocker | Unblocked by | Owner |
|---|---|---|
| No dataset files | Download IBM HI-Small, LI-Small, **HI-Medium**, LI-Medium + pattern files; run the profiler; send the aggregate outputs | You |
| Kaggle licence field unread | Copy the licence field of the IBM Kaggle page into `DATA_LICENCE_AUDIT.md` | You |
| Authors' reply on post-period all-laundering transactions | Read the Kaggle discussion "response to Marco"; paste it | You |
| SAML-D licence | Read Kaggle licence field; if missing/unclear, email the corresponding author | You |
| Literature protocol | Run the residual queries in Semantic Scholar / Scopus / ACM / IEEE (`LIT_SEARCH_LOG.md` §3) | You |
| RQ/H freeze | Profiler results → apply the pre-declared decision rules (`RESEARCH_SPEC_v1_PROVISIONAL.md` §22) | Both |
| Deadline | Tell me the submission date; tier scope depends on it | You |

## Pre-declared freeze procedure
1. Profiler outputs received for HI-Small and HI-Medium.
2. Apply the decision rules in `RESEARCH_SPEC_v1_PROVISIONAL.md` §22 mechanically; record which branch fired.
3. If all critical items are YES: rename the provisional spec to `RESEARCH_SPEC_v1.md`, mark it frozen, update this file.
4. Only then: modelling code (baseline features → H1), in that order.

**Still forbidden before step 3:** modelling, feature engineering beyond profiling, frontend, deployment, LLM, GNN.
