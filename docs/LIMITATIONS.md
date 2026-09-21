# LIMITATIONS

Genuine limitations of this build. Results are in `RESULTS.md`; read them with this list.

## Evidence
1. **Synthetic data, one generator, reduced scale.** Tide at 1,500 individuals (not the published ~36.6 k-node release, whose size and licence could not be verified). LI and HI share one population and are **not independent datasets**. Nothing here says anything about real-world AML.
2. **Very few independent schemes.** The primary (new-scheme) test stream has 8 schemes (LI) and 15 (HI), so every interval is wide and fragile. Cases within a scheme are dependent; intervals resample schemes for that reason.
3. **H2 is underpowered.** Held-out families have 1–8 schemes in the evaluation window (one family has a single scheme, giving a degenerate interval). No pooled claim is made.
4. **A generator artefact carries much of the signal.** ~98 % of positives are `transfer` transactions and `payment` never carries fraud. Removing transaction-type features lowers recall@K markedly; conclusions about "detectability" would be unsafe.
5. **Graph features showed no measurable benefit here.** This is a result about this generator and scale, not evidence that graph methods cannot help. No GNN was tried.
6. **Prevalence mismatch.** Training case prevalence (≈ 0.30 %) is far above the new-scheme test prevalence (≈ 0.068 %); capacity is anchored to the training figure by design, which changes what "m = 1" means on the test stream.
7. **The strict view discards ongoing schemes** (534 → 216 positive cases on LI) to avoid contamination; the "all" view is inflated by carry-over. Neither is "the" real-world number.
8. **Calibration is weak.** Brier skill over a prevalence-only predictor is single-digit percent; ECE is not informative at this prevalence.

## Decision engine
9. **Capacity dominates.** At m = 1 roughly 60 % of positives are never reviewed; auto-closing only decides what happens to them. "Workload removed" (≈ 90–95 % of *cases*) is dominated by trivially low-risk cases and must not be read as analyst hours saved. No savings estimate is made.
10. **No conformal guarantee is claimed.** Exchangeability is violated (scheme clustering, time order, constructed shift). The engine measures violation instead. If only reviewed cases' labels are ever known (selection bias), the conformal policy fails badly (see `RESULTS.md`).
11. Label delay, backlog expiry, window length and capacity rule are modelling choices, not calibrated to any institution.

## Product / engineering
12. **Demo data are a sample:** 240 alerts per dataset chosen by a stated rule from the real review queue (979 / 1,768 cases); dashboard figures come from the full simulation, the alert list from the sample.
13. **Analyst feedback is simulated.** In demo mode decisions live in the visitor's browser; in live mode on a free host SQLite is ephemeral (see `DEPLOYMENT.md`).
14. **Monitoring is a backtest replay**, not live monitoring.
15. **Amounts are nominal**: the generator does not convert currencies, so sums across currencies are not monetary values.
16. **SHAP explains the model, not the world**; correlated features share credit; reason codes group features and add no information.
17. **Not verified in a real browser.** No Playwright/Chromium was available; end-to-end coverage is jsdom-level plus API contract tests. The CSP was validated by header inspection only.
18. **Not deployed by this build.** No Vercel/Render account was available; URLs in `DEPLOYMENT.md` are placeholders. The Dockerfile was not built here.
19. **AMLNet adapter is unverified** (Zenodo unreachable); TransXion and IBM were not used for results.
20. No fairness analysis (synthetic data carry no protected attributes) and no adversarial-robustness testing.
