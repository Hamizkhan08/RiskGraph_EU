# ml/profiling — Gate 0.5 profiling instrument

**What it is:** a read-only profiler that answers the file-level questions Gate 0.5 could not (`docs/GATE_0_5_AUDIT.md`, `docs/UNIT_OF_ANALYSIS.md`). **It contains no features, no models, no training.**

**What it is not yet:** validated on the real files. It has been tested only on synthetic fixtures (`tests/test_profile_dataset.py`, 7 tests, expected values computed independently) and a 2M-row synthetic speed check (12 s, < 2 GB).

## Run it (you, locally — Kaggle is not reachable from the working sandbox)

```bash
pip install pandas numpy matplotlib tabulate      # tabulate optional
kaggle datasets download -d ealtman2019/ibm-transactions-for-anti-money-laundering-aml -p data/raw --unzip
# do NOT commit data/raw (see docs/DATA_LICENCE_AUDIT.md)

python ml/profiling/profile_dataset.py --schema ibm \
  --transactions data/raw/HI-Small_Trans.csv --patterns data/raw/HI-Small_Patterns.txt \
  --primary-end 2022-09-10 --out artifacts/profiling/HI-Small

python ml/profiling/profile_dataset.py --schema ibm \
  --transactions data/raw/HI-Medium_Trans.csv --patterns data/raw/HI-Medium_Patterns.txt \
  --primary-end 2022-09-16 --test-days 5 --out artifacts/profiling/HI-Medium
```
Also run LI-Small and LI-Medium (the untyped share differs sharply between HI and LI).
File names above are the *expected* ones; if the header check or file names differ, the script stops and tells you.

**If it fails on the header or on `W_PATTERN_MISMATCH`:** the assumed formats are wrong (pattern-file layout, timestamp format). Send me the first 5 lines of the transactions file and the first 12 lines of the patterns file (they are synthetic records; CDLA-Sharing-1.0 allows sharing subsets with attribution — see `docs/DATA_LICENCE_AUDIT.md`; not legal advice).

## What to send back
`artifacts/profiling/<name>/profile_report.md`, `profile_report.json`, `typology_table.csv`, `split_feasibility.csv`, `temporal.png`. These are aggregate outputs (no rows).

## Outputs
| File | Content |
|---|---|
| `profile_report.md/json` | counts, laundering prevalence, post-period tail, account-days (A) and k-day blocks (B), roles, persistence, pattern coverage, scheme/account overlap, warnings |
| `per_day.csv` | transactions, laundering, account-days, positive account-days per day |
| `typology_table.csv`, `family_table.csv` | per typology/family counts and the pre-declared suitability rule |
| `split_feasibility.csv` | candidate temporal layouts with test-block sizes and resolution |
| `temporal.png`, `typology.png` | plots |

## Assumptions to verify (flagged `[U]` in the audit)
1. IBM header: `Timestamp, From Bank, Account, To Bank, Account, Amount Received, Receiving Currency, Amount Paid, Payment Currency, Payment Format, Is Laundering`.
2. Timestamp format `YYYY/MM/DD HH:MM` (falls back automatically and reports the format used).
3. Pattern file: `BEGIN LAUNDERING ATTEMPT - <TYPE>: …` / transaction rows in the same 11-column layout / `END LAUNDERING ATTEMPT …`.
4. SAML-D column names (`Time, Date, Sender_account, Receiver_account, Amount, Payment_currency, Received_currency, …, Is_laundering, Laundering_type`).

## Scale limits (honest)
- In-memory numpy/pandas, chunked reading. Small (5–7M rows): seconds to minutes.
- Medium (≈32M rows): expect several minutes and **several GB of RAM (estimate, untested)**; use `--skip-duplicates` if memory is tight.
- Large (≈180M rows): not supported by this design; would need DuckDB/Polars.
- Only positive rows are matched against pattern keys, so pattern matching is cheap.
