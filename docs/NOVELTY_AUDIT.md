# NOVELTY_AUDIT.md

Date: 20 September 2026 · Inputs: `LIT_SEARCH_LOG.md`, `PRIOR_ART_MATRIX.md`

## Classification: **Case B — partial overlap, with a meaningful evaluation gap remaining**
Confidence: **moderate**. The search was a general web search, not the Semantic Scholar / Scopus / ACM / IEEE protocol you specified (`LIT_SEARCH_LOG.md` §3). **Case A ("strongly supported gap") is not claimed and cannot be claimed from this session.**

## Why not Case A
A gap is "strongly supported" only after a documented multi-database search finds nothing close. That search is incomplete here, and the search that *was* run found substantial neighbours:
- capacity-style metrics on public data with a chronological split (Nahimana & Gaba 2026, on SAML-D);
- graph features for triage on real bank data (Naser Eddin et al.);
- conformal prediction on temporal AML graphs (NCPNET);
- structural-perturbation robustness on AMLworld (TU Delft thesis) and generator dependence (Tide).

## Why not Case C (saturated)
None of the works read combine (a) **held-out structural families** as the shift, (b) a **formally specified review / auto-close / backlog policy**, and (c) a **realised miss rate** measured against complete synthetic labels. No study of recall-controlled auto-closure under typology shift was found.

## Why not Case D (dataset limitation) — yet
The question is testable on IBM-Medium for H1 and H3. H2 is *conditionally* testable: IBM's typology labels cover only 19–62% of laundering and its families overlap structurally (`GATE_0_5_AUDIT.md` §5). Case D becomes true for H2 if profiling shows the §5 sample rule fails on IBM-Medium and SAML-D is unusable.

## Component verdicts
| Component | Verdict |
|---|---|
| Capacity / top-K metrics | **Not novel.** Use as method, not as contribution |
| Graph features improve triage | **Not novel;** H1 is an extension under a stricter protocol. Expect a small or null effect (Deprez found only egonet-type features helped on IBM) |
| Held-out **family** evaluation of capacity metrics (H2) | **Not found.** Closest: per-pattern in-distribution recall; perturbation robustness |
| Risk-controlled auto-closure with realised miss rate under shift (H3) | **Not found.** Closest: NCPNET (coverage, not closure); vendor claims (unverifiable) |
| The combination and the *measured failure of guarantees* under clustered, ordered, shifted data | **Not found;** the defensible contribution |

## What the contribution is — and is not
- **Is:** an evaluation protocol and empirical evidence on (i) whether graph context survives family shift and (ii) how far a conformal-calibrated closure rule's realised miss rate departs from its nominal tolerance, with negative results reported.
- **Is not:** a new model, a detection system, a bank-effectiveness claim, or a proof of a guarantee.

## Kill / pivot criteria (pre-declared)
| Trigger | Action |
|---|---|
| Residual literature search finds a study that holds out structural families/typologies *and* reports capacity metrics | Re-classify (probably Case C); rewrite RQ around H3 only or pivot |
| Residual search finds recall-controlled / conformal auto-closure evaluated under distribution shift on AML data | Reduce H3 to a replication; re-audit |
| Profiling: H2 fails the sample rule on IBM-Medium **and** SAML-D fails licence/span checks | Drop H2 (Option D-lite, `GATE_0_5_AUDIT.md` §17); novelty re-audited, may become Case C |
| Profiling: post-period tail or untyped laundering makes H1 uninterpretable | Report typed/untyped separately; if still uninterpretable, restrict H1 to typed cases and say so |
