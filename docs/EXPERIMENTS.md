# EXPERIMENTS — protocol and reproduction

Every reported number is produced by `riskgraph/experiments.py`, stored under `artifacts/runs/<run_id>/`, and rendered into `RESULTS.md` by `scripts/render_results.py`. Nothing is typed by hand; `artifacts/results_manifest.json` traces each figure to its run, dataset, split, feature version, model, seeds and source file.

## Pre-declared constants
See `riskgraph/config.py` and `RESEARCH_SPEC_FINAL.md` §6 (seeds 11/23/37, split fractions, capacity multipliers, α grid, label delay, expiry, window, bootstrap resamples, fixed LightGBM parameters — **no tuning**).

## Stages
| Stage | Question | Output |
|---|---|---|
| H1 | Does adding graph context (G) to T+B raise recall@K at fixed capacity? Plus ablations (T only; without transaction-type features) and calibration | `h1.json` |
| H2 | When a structural family is held out, do typology-aware features (M) lose less recall than generic ones? | `h2.json` |
| H3 | Does the realised miss rate of auto-closed positives stay near its nominal α under static / rolling / conformal-corrected policies, in the same regime and with a held-out family? | `h3.json` |
| Export | Queue sample, SHAP explanations, evidence, monitoring replay, model, score stream | `artifacts/demo/<DS>/` |

## Run manifest fields
`run_id`, UTC timestamp, pipeline and feature versions, dataset provenance (generator commit, seed, config, SHA-256 of the input files), unit of analysis, train / validation / purge / test dates, seeds, LightGBM parameters, capacity rule and grid, policy constants, calibration policy, evaluation views, model → feature lists, bootstrap settings.

## Reproduce
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
git clone https://github.com/mntijn/Tide.git ../Tide
python scripts/generate_tide.py --tide ../Tide --variant li --out data/raw/tide_li     # ~70 s, ~2.3 GB RAM
python scripts/generate_tide.py --tide ../Tide --variant hi --out data/raw/tide_hi
python scripts/run_experiments.py --data data/raw/tide_li                                # ~9 min on one core
python scripts/run_experiments.py --data data/raw/tide_hi
python scripts/build_bundle.py --li data/raw/tide_li --hi data/raw/tide_hi
python scripts/render_results.py && python scripts/render_api_docs.py
```
`run_experiments.py` is resumable: stage outputs are persisted, so re-running only recomputes missing stages (and always H3). Use a Tide clone at the commit recorded in `artifacts/runs/*/manifest.json` for an identical population.

## Reproducibility notes
* Data are **regenerated**, not downloaded: the generator is stochastic with a fixed seed, so use the same commit and config. The Zenodo release of Tide was not used (see `DATA_CARD.md`).
* One CPU core / 4 GB RAM shaped the scale (1,500 individuals) and the number of seeds (3).
* The manifest timestamp reflects the last stage that was re-run (H3 was re-run to add intervals; H1/H2 outputs are unchanged).
* Deviations from the pre-declaration are listed in `RESEARCH_SPEC_FINAL.md` §10.
