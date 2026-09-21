# DATA CARD

## Provenance
Synthetic transactions generated **locally** with the MIT-licensed [Tide](https://github.com/mntijn/Tide) generator (commit recorded in each run manifest: `522ccebf266d6a77ddf29e59725d5b27a5a8a0a3`), via `scripts/generate_tide.py`.
* **Not** the Zenodo release (`10.5281/zenodo.18804069`): unreachable from the build environment; its licence and the quoted size (~36.6 k nodes / 7.6 M edges) are **unverified**.
* Reduced scale: 1,500 individuals (repo default 8,000), 12 months, seed 42. LI-like = 60 illicit patterns; HI-like = 107 (the repository's 180:320 ratio). Same 5,158 accounts in both.

## Measured properties (from `artifacts/runs/*/data_quality.json`; see RESULTS.md)
* LI-like ≈ 0.103 % and HI-like ≈ 0.197 % illicit transactions (close to the 0.10 / 0.19 % the paper reports for the released files).
* **100 % of fraud transactions match exactly one pattern instance; 0 non-fraud rows match.** (Contrast: IBM 19–62 %.)
* Scheme durations are long — median ≈ 13 days, p95 ≈ 214 days, maximum ≈ 344 days — hence the scheme-start rule.
* ≈ 98 % of positives are `transfer`; `payment` never contains fraud → **near-giveaway artefact**, handled by the A2 ablation.
* A handful of rows after the configured end date are all fraud → excluded.
* 5 pattern families: SynchronisedTransactions, FrontBusinessActivity, UTurnTransactions, RapidFundMovement, RepeatedOverseasTransfers.

## Used / excluded
* Used: `generated_transactions.csv` (src, dest, amount, currency, timestamp, transaction_type, is_fraudulent), `generated_patterns.json`.
* Excluded on purpose: `generated_nodes.csv` (node-level `is_fraudulent`, `risk_score`, high-risk flags — generator-side selection inputs), ownership edges, `time_since_previous_transaction`.
* Amounts carry a currency code but the generator applies **no FX conversion**; aggregates are "nominal units".

## Other datasets
AMLNet v2.0 (CC BY-NC 4.0; record verified): not used — see spec §1; adapter `riskgraph/data/amlnet.py` is experimental and tested only on a synthetic file in the documented schema. TransXion: not investigated beyond the summary supplied; licence unverified. IBM AMLworld: legacy profiling instrument only (`ml/profiling/`).

## Personal data
None: all identifiers are synthetic. No real transactions, no personal data.

## Regeneration
`git clone https://github.com/mntijn/Tide.git ../Tide && python scripts/generate_tide.py --tide ../Tide --variant li --out data/raw/tide_li` (and `--variant hi`). ~70 s and ~2.3 GB RAM each. Raw data is git-ignored and not shipped.
