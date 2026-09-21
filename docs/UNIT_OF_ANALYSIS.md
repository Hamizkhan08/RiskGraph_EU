# UNIT_OF_ANALYSIS.md — Is "account-day" a sound case definition?

Date: 20 September 2026 · Status: **provisional decision; empirical checks pending the profiler** · Part of Gate 0.5 (`GATE_0_5_AUDIT.md`)

Everything below that requires counts from the files is marked **[profiler]**. No number here comes from the data.

---

## 1. Definitions compared

| | Definition A — account-day | Definition B1 — non-overlapping 3-day block | Definition B2 — rolling 3-day window |
|---|---|---|---|
| Case | account × calendar day | account × block of 3 consecutive days | account × trailing 3 days, re-scored every day |
| Label | account is sender or receiver of ≥ 1 laundering-tagged transaction that day | … within the block | … within the window |
| Cases per account | up to 10 (Small) / 16 (Medium) | up to 3–4 / 5 | up to 10 / 16, but each event appears in 3 windows |
| Review cadence | daily (matches "daily capacity") | once per block | daily |

---

## 2. Criteria and assessment

| Criterion | A | B1 | B2 |
|---|---|---|---|
| Matches a "per-day review capacity" | ✔ natural | ✘ capacity becomes per-3-days | ✔ |
| Number of independent review cycles in the data | 10 / 16 | **3 / 5** — too few to evaluate backlog dynamics | 10 / 16 |
| Correlated duplicate cases | one scheme → several correlated cases (one per active day) | fewer | **worst:** every positive event enters 3 cases, inflating counts and dependence |
| Day-boundary artefacts | schemes crossing midnight are split | reduced | reduced |
| Leakage control | simple: features ≤ end of day | window straddles the split cut more often | window straddles cut every day |
| Comparability with published work | weaker (transaction-level dominates) | — | — |
| Fits capacity/backlog formalisation (`GATE_0_5_AUDIT.md` §12) | ✔ | ✘ | ✔ but duplicates |

**Assessment.**
- **B1 fails structurally:** with 10–16 days it leaves 3–5 cases per account and 3–5 review cycles in total; the capacity/backlog experiment cannot be run.
- **B2 fails statistically:** it multiplies the same laundering event across three overlapping cases, so raw counts overstate independent information.
- **A works operationally** and is compatible with the formalisation. Its weakness — splitting multi-day schemes and day-boundary effects — is addressed by (i) **trailing-window features** (e.g. last 3 days) attached to each account-day case, and (ii) **scheme-level clustering** in the statistics. Windowing is therefore moved from the *case* to the *features*.

## 3. Provisional decision
**Adopt Definition A (account-day) as the case unit, with trailing-window features.** Definition B is *not* adopted as a competing unit, but a 3-day **label** variant is reported as a sensitivity analysis only if the checks below show severe day-splitting.

---

## 4. Pre-declared checks (all produced by `ml/profiling/profile_dataset.py`)

| # | Check | Why it matters | Decision rule |
|---|---|---|---|
| U1 | Number of account-days, positive account-days, prevalence (A and B1) | Sizes the problem and sets the capacity grid (`GATE_0_5_AUDIT.md` §13) | Need ≥ 200 positive account-days **in the test block**; otherwise the unit is too sparse |
| U2 | Accounts active on many days | Repeated-account dependence | Report distribution; drives the cluster-resampling check |
| U3 | **Label persistence:** share of positive account-days whose account is also positive the previous/next day | One scheme → many correlated cases | If > 60% persist, expect strong dependence; keep A but rely on scheme clusters, do not use case counts as sample size |
| U4 | Positive account-days per scheme (needs scheme identity) | Effective sample size = schemes, not cases | Reported alongside raw counts |
| U5 | Share of pattern blocks (schemes) spanning > 1 calendar day | Midnight splitting | If > 50%, add 3-day *label* sensitivity; still keep A |
| U6 | **Role asymmetry:** positive account-days by role — sender-only / receiver-only / both | Transitive tagging makes receivers positive regardless of their own behaviour | Primary label **L1 = any involvement**. If receiver-only > 50% of positives, add **L2 = sender-of-laundering-tagged flow** as a sensitivity label |
| U7 | Transitivity effect: positives that occur only via untyped ("integration") transactions | These look like ordinary payments; mostly undetectable | Report **typed vs untyped** positives separately in every result |
| U8 | Post-period tail: transactions after the primary period end, and their laundering share | Tail is documented as all-laundering → timestamp leak | Exclude the tail from cases; report its size; never use absolute time as a feature |
| U9 | Cold-start: share of test-block cases with < 1 day of history | Trailing features are empty early on | Burn-in of 2 days; report share of cases affected |

---

## 5. Semantics to keep honest
- A positive case means **"an account touched by a laundering-tagged flow that day"**. Under transitive tagging it can include the receiver of a disguised integration payment (payroll, supplies) — an account that may look entirely ordinary.
- Wording in all documents, UI and dissertation: *risk signal / case / priority*. Never "criminal account" or "launderer".
- The IBM data provide **account** identifiers only. Entity-level resolution (one entity owning several accounts) is not available, so the case is an account, not a customer.

## 6. What would change the decision
- If U8 shows the tail dominates the last days of the timeline, the effective test block shrinks and the temporal layout must be recomputed **before** choosing a unit.
- If U3–U5 show that nearly all schemes fit inside one day and rarely reuse accounts, A is confirmed with the plain scheme-cluster design.
- If U1 shows fewer than ~200 positive account-days in a candidate test block, extend the block or move to a larger slice — do **not** shrink the unit.
