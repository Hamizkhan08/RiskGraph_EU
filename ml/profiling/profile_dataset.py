#!/usr/bin/env python3
"""Gate 0.5 profiling instrument for RiskGraph EU.

PURPOSE   Settle the FILE-LEVEL questions left open by docs/GATE_0_5_AUDIT.md:
          schema, counts, date span, post-period tail, laundering counts, pattern/typology
          coverage, account-day counts, split feasibility, leakage warnings.
SCOPE     Profiling only. NO features, NO models, NO training.
STATUS    Tested only on a synthetic fixture (tests/test_profile_dataset.py).
          The IBM pattern-file format is ASSUMED (see parse_patterns); the parser fails loudly
          and reports what it found rather than guessing.

Usage (IBM AMLworld):
  python ml/profiling/profile_dataset.py --schema ibm \
      --transactions data/raw/HI-Small_Trans.csv --patterns data/raw/HI-Small_Patterns.txt \
      --primary-end 2022-09-10 --out artifacts/profiling/HI-Small

Usage (SAML-D; typology comes from the Laundering_type column, no patterns file):
  python ml/profiling/profile_dataset.py --schema samld --transactions data/raw/SAML-D.csv \
      --out artifacts/profiling/SAML-D
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------------------
IBM_COLS = [
    "timestamp",
    "from_bank",
    "src",
    "to_bank",
    "dst",
    "amount_received",
    "receiving_currency",
    "amount_paid",
    "payment_currency",
    "payment_format",
    "y",
]
IBM_HEADER = [
    "timestamp",
    "from bank",
    "account",
    "to bank",
    "account",
    "amount received",
    "receiving currency",
    "amount paid",
    "payment currency",
    "payment format",
    "is laundering",
]
IBM_KEYCOLS = IBM_COLS[:10]  # raw fields used to match pattern-file lines (label excluded)

# Structural families proposed in docs/GATE_0_5_AUDIT.md §11 (H2). Subject to revision after profiling.
FAMILY_RULES = [  # (substrings that must ALL be present in the normalised name, family)
    (("FAN", "OUT"), "F1_fan"),
    (("FAN", "IN"), "F1_fan"),
    (("SCATTER", "GATHER"), "F1_fan"),
    (("GATHER", "SCATTER"), "F1_fan"),
    (("CYCLE",), "F2_cycle"),
    (("BIPARTITE",), "F3_biclique"),
    (("STACK",), "F3_biclique"),
    (("RANDOM",), "F4_random"),
]

TS_FORMATS = ["%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", None]


def norm_name(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum() or ch == " ").replace("  ", " ")


def family_of(name: str) -> str:
    n = norm_name(name).replace(" ", "")
    # order matters: SCATTERGATHER / GATHERSCATTER must be tested before FAN-IN / FAN-OUT substrings
    for parts, fam in FAMILY_RULES:
        if all(p in n for p in parts):
            return fam
    return "UNMAPPED"


def wilson_halfwidth(n: int, p: float = 0.5, z: float = 1.96) -> float:
    if n <= 0:
        return float("nan")
    d = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d


def hash_str(s: pd.Series) -> np.ndarray:
    return pd.util.hash_pandas_object(s, index=False).to_numpy(dtype="uint64")


def parse_ts(s: pd.Series, fmt: str | None) -> pd.Series:
    if fmt is None:
        return pd.to_datetime(s, errors="coerce")
    return pd.to_datetime(s, format=fmt, errors="coerce")


def pick_ts_format(sample: pd.Series) -> str | None:
    best, best_fail = None, 2.0
    for f in TS_FORMATS:
        fail = parse_ts(sample, f).isna().mean()
        if fail < best_fail:
            best, best_fail = f, fail
        if fail < 0.01:
            break
    return best


def day_ordinal(ts: pd.Series) -> np.ndarray:
    """Integer days since epoch (NaT -> -1)."""
    d = ts.dt.normalize().dt.as_unit("ns")  # pandas >=3 may infer s/us; force ns
    out = (d.astype("int64") // 86_400_000_000_000).to_numpy()
    out = np.where(ts.isna().to_numpy(), -1, out)
    return out.astype("int64")


def group_or(a: np.ndarray, d: np.ndarray, r: np.ndarray):
    """Unique (a,d) pairs; OR-reduce r within each pair."""
    if len(a) == 0:
        return a, d, r
    order = np.lexsort((d, a))
    a, d, r = a[order], d[order], r[order]
    new = np.r_[True, (a[1:] != a[:-1]) | (d[1:] != d[:-1])]
    idx = np.flatnonzero(new)
    return a[idx], d[idx], np.bitwise_or.reduceat(r, idx)


# --------------------------------------------------------------------------------------
# Pattern file (IBM) — FORMAT ASSUMED, verified at runtime
# --------------------------------------------------------------------------------------
def parse_patterns(path: Path, ts_fmt: str | None):
    """Return list of blocks: dict(id, typology, keys, day_min, day_max, accounts).

    Assumed format (unverified against the real file):
        BEGIN LAUNDERING ATTEMPT - <TYPOLOGY>: <free text>
        <same 11 CSV fields as the transactions file>
        ...
        END LAUNDERING ATTEMPT - <TYPOLOGY>
    """
    blocks, cur, n_lines, n_unparsed = [], None, 0, 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            up = line.upper()
            if up.startswith("BEGIN LAUNDERING ATTEMPT"):
                hdr = line[len("BEGIN LAUNDERING ATTEMPT") :].strip(" -:")
                typ = hdr.split(":")[0].strip().upper()
                cur = {"id": len(blocks), "typology": typ, "keys": [], "ts": [], "acc": []}
            elif up.startswith("END LAUNDERING ATTEMPT"):
                if cur is not None:
                    blocks.append(cur)
                cur = None
            elif cur is not None:
                f = [x.strip() for x in line.split(",")]
                n_lines += 1
                if len(f) < 10:
                    n_unparsed += 1
                    continue
                cur["keys"].append(",".join(f[:10]))
                cur["ts"].append(f[0])
                cur["acc"].extend([f[2], f[4]])
    if cur is not None:  # unterminated block
        blocks.append(cur)
    out = []
    for b in blocks:
        ts = parse_ts(pd.Series(b["ts"]), ts_fmt)
        days = day_ordinal(ts)
        days = days[days >= 0]
        out.append(
            {
                "id": b["id"],
                "typology": b["typology"],
                "keys": b["keys"],
                "day_min": int(days.min()) if len(days) else -1,
                "day_max": int(days.max()) if len(days) else -1,
                "accounts": set(b["acc"]),
            }
        )
    return out, {"pattern_lines": n_lines, "pattern_lines_unparsed": n_unparsed, "blocks": len(out)}


# --------------------------------------------------------------------------------------
# Chunk reading
# --------------------------------------------------------------------------------------
def read_chunks(schema: str, path: Path, chunksize: int, max_rows: int | None):
    if schema == "ibm":
        with open(path, encoding="utf-8", errors="replace") as fh:
            header = [h.strip().lower() for h in fh.readline().strip().split(",")]
        if header != IBM_HEADER:
            sys.exit(
                f"[FAIL] IBM header differs from the assumed schema.\n  found:    {header}\n"
                f"  expected: {IBM_HEADER}\nFix IBM_HEADER/IBM_COLS after inspecting the file."
            )
        it = pd.read_csv(
            path,
            header=None,
            skiprows=1,
            names=IBM_COLS,
            dtype=str,
            keep_default_na=False,
            chunksize=chunksize,
            nrows=max_rows,
        )
        for c in it:
            yield c
    else:
        head = pd.read_csv(path, nrows=0)
        cols = {c: c.strip().lower().replace(" ", "_") for c in head.columns}
        want = {
            "time",
            "date",
            "sender_account",
            "receiver_account",
            "amount",
            "payment_currency",
            "received_currency",
            "payment_type",
            "is_laundering",
            "laundering_type",
        }
        missing = want - set(cols.values())
        if missing:
            sys.exit(
                f"[FAIL] SAML-D columns missing after normalisation: {sorted(missing)}\n"
                f"       found: {sorted(cols.values())}"
            )
        it = pd.read_csv(path, dtype=str, keep_default_na=False, chunksize=chunksize, nrows=max_rows)
        for c in it:
            c = c.rename(columns=cols)
            out = pd.DataFrame(
                {
                    "timestamp": c["date"].str.strip() + " " + c["time"].str.strip(),
                    "src": c["sender_account"],
                    "dst": c["receiver_account"],
                    "amount_received": c["amount"],
                    "amount_paid": c["amount"],
                    "receiving_currency": c["received_currency"],
                    "payment_currency": c["payment_currency"],
                    "payment_format": c["payment_type"],
                    "y": c["is_laundering"],
                    "typology": c["laundering_type"],
                }
            )
            yield out


# --------------------------------------------------------------------------------------
# Main profiling
# --------------------------------------------------------------------------------------
def profile(args) -> dict:
    tx_path = Path(args.transactions)
    ts_fmt, first = "UNSET", True
    R: dict = {"schema": args.schema, "transactions_file": str(tx_path)}
    n_rows = n_bad_ts = n_bad_label = n_selfloop = n_nonpos_amt = n_nan_amt = 0
    null_counts: Counter = Counter()
    per_day: dict[int, list[int]] = {}
    curr_r, curr_p, fmt_c = Counter(), Counter(), Counter()
    amt_sample: list[np.ndarray] = []
    rowhash: list[np.ndarray] = []
    A_list, D_list = [], []  # all endpoints in-period
    PA, PD, PR = [], [], []  # positive endpoints in-period (+role bits)
    acct_bank_a, acct_bank_b = [], []
    tail_rows = tail_pos = 0
    pat_map: dict[str, list[int]] = {}
    blocks, pat_info = [], {}
    primary_end_day = None
    rng = np.random.default_rng(0)
    typ_rows: list[tuple] = []  # (acct_hash, day, typ_index) for matched positives
    typ_names: list[str] = []
    typ_index: dict[str, int] = {}
    pos_tx_total = pos_tx_typed = pos_tx_multi = 0
    matched_keys: set[str] = set()
    pos_tx_untyped_days: Counter = Counter()

    if args.primary_end:
        primary_end_day = int(pd.Timestamp(args.primary_end).value // 86_400_000_000_000)

    for chunk in read_chunks(args.schema, tx_path, args.chunksize, args.max_rows):
        n = len(chunk)
        n_rows += n
        for c in chunk.columns:
            null_counts[c] += int((chunk[c].str.strip() == "").sum())
        if first:
            ts_fmt = pick_ts_format(chunk["timestamp"].head(50_000))
            R["timestamp_format_used"] = ts_fmt if ts_fmt is not None else "inferred (no fixed format)"
            if args.schema == "ibm" and args.patterns:
                blocks, pat_info = parse_patterns(Path(args.patterns), ts_fmt)
                for b in blocks:
                    for k in b["keys"]:
                        pat_map.setdefault(k, []).append(b["id"])
            first = False
        ts = parse_ts(chunk["timestamp"], ts_fmt)
        bad = ts.isna().to_numpy()
        n_bad_ts += int(bad.sum())
        y_num = pd.to_numeric(chunk["y"], errors="coerce")
        n_bad_label += int(y_num.isna().sum())
        y = y_num.fillna(0).to_numpy().astype("int8")
        day = day_ordinal(ts)
        src_h, dst_h = hash_str(chunk["src"]), hash_str(chunk["dst"])
        n_selfloop += int((src_h == dst_h).sum())

        # amounts
        amt = pd.to_numeric(chunk["amount_paid"], errors="coerce").to_numpy()
        n_nan_amt += int(np.isnan(amt).sum())
        n_nonpos_amt += int((amt[~np.isnan(amt)] <= 0).sum())
        valid_amt = amt[~np.isnan(amt)]
        if len(valid_amt):
            amt_sample.append(rng.choice(valid_amt, size=min(20_000, len(valid_amt)), replace=False))

        # categorical distributions
        curr_r.update(chunk["receiving_currency"].value_counts().to_dict())
        curr_p.update(chunk["payment_currency"].value_counts().to_dict())
        fmt_c.update(chunk["payment_format"].value_counts().to_dict())

        # duplicates (full raw row)
        if not args.skip_duplicates:
            rowhash.append(pd.util.hash_pandas_object(chunk, index=False).to_numpy(dtype="uint64"))

        # per-day counts (all rows with a valid timestamp)
        g = pd.DataFrame({"d": day, "y": y})
        g = g[g["d"] >= 0].groupby("d")["y"].agg(["size", "sum"])
        for d_, (sz, sm) in g.iterrows():
            v = per_day.setdefault(int(d_), [0, 0])
            v[0] += int(sz)
            v[1] += int(sm)

        in_period = (day >= 0) if primary_end_day is None else ((day >= 0) & (day <= primary_end_day))
        if primary_end_day is not None:
            after = day > primary_end_day
            tail_rows += int(after.sum())
            tail_pos += int((y[after] == 1).sum())

        # endpoints for account-day construction
        m = in_period
        A_list.append(np.concatenate([src_h[m], dst_h[m]]))
        D_list.append(np.concatenate([day[m], day[m]]))
        mp = m & (y == 1)
        PA.append(np.concatenate([src_h[mp], dst_h[mp]]))
        PD.append(np.concatenate([day[mp], day[mp]]))
        PR.append(np.concatenate([np.ones(mp.sum(), dtype="uint8"), np.full(mp.sum(), 2, dtype="uint8")]))

        # account -> bank stability (IBM only)
        if args.schema == "ibm":
            bank_s = hash_str(chunk["from_bank"])
            bank_d = hash_str(chunk["to_bank"])
            acct_bank_a.append(np.concatenate([src_h, dst_h]))
            acct_bank_b.append(np.concatenate([bank_s, bank_d]))

        # typology assignment for positives
        pos_idx = np.flatnonzero(y == 1)
        pos_tx_total += len(pos_idx)
        if len(pos_idx):
            sub = chunk.iloc[pos_idx]
            if args.schema == "ibm" and blocks:
                keys = sub[IBM_KEYCOLS].agg(",".join, axis=1).to_numpy()
                for j, k in enumerate(keys):
                    bl = pat_map.get(k)
                    i = pos_idx[j]
                    if bl:
                        matched_keys.add(k)
                    if not in_period[i]:
                        continue
                    if bl:
                        typs = sorted({blocks[b]["typology"] for b in bl})
                        pos_tx_typed += 1
                        pos_tx_multi += int(len(typs) > 1)
                        for t in typs:
                            ti = typ_index.setdefault(t, len(typ_names))
                            if ti == len(typ_names):
                                typ_names.append(t)
                            typ_rows.append((src_h[i], day[i], ti))
                            typ_rows.append((dst_h[i], day[i], ti))
                    else:
                        pos_tx_untyped_days[int(day[i])] += 1
            elif args.schema == "samld":
                for j, t in enumerate(sub["typology"].to_numpy()):
                    i = pos_idx[j]
                    if not in_period[i]:
                        continue
                    t = (t or "").strip().upper() or "UNTYPED"
                    ti = typ_index.setdefault(t, len(typ_names))
                    if ti == len(typ_names):
                        typ_names.append(t)
                    pos_tx_typed += 1
                    typ_rows.append((src_h[i], day[i], ti))
                    typ_rows.append((dst_h[i], day[i], ti))

    # ------------------------------------------------------------------ assemble
    days_sorted = sorted(per_day)
    R["rows"] = n_rows
    R["null_counts"] = dict(null_counts)
    R["timestamp_unparseable"] = n_bad_ts
    R["label_unparseable"] = n_bad_label
    R["self_loops"] = n_selfloop
    R["amount_nonpositive"] = n_nonpos_amt
    R["amount_nan"] = n_nan_amt
    R["receiving_currency_counts"] = dict(curr_r.most_common())
    R["payment_currency_counts"] = dict(curr_p.most_common())
    R["payment_format_counts"] = dict(fmt_c.most_common())
    samp = np.concatenate(amt_sample) if amt_sample else np.array([])
    if len(samp):
        R["amount_paid_quantiles(sampled)"] = {str(q): float(np.quantile(samp, q)) for q in (0, 0.01, 0.5, 0.99, 1)}
    if not args.skip_duplicates and rowhash:
        h = np.concatenate(rowhash)
        R["duplicate_rows"] = int(len(h) - len(np.unique(h)))
    n_pos_all = sum(v[1] for v in per_day.values())
    R["laundering_transactions_all_rows"] = int(n_pos_all)
    R["laundering_prevalence_all_rows"] = n_pos_all / max(n_rows, 1)
    if days_sorted:
        d0 = days_sorted[0]
        R["date_min"] = str(pd.Timestamp(days_sorted[0] * 86_400_000_000_000).date())
        R["date_max"] = str(pd.Timestamp(days_sorted[-1] * 86_400_000_000_000).date())
        R["distinct_days"] = len(days_sorted)
        pdays = pd.DataFrame(
            [
                {
                    "day_index": d - d0 + 1,
                    "date": str(pd.Timestamp(d * 86_400_000_000_000).date()),
                    "tx": per_day[d][0],
                    "laundering_tx": per_day[d][1],
                    "laundering_share": per_day[d][1] / per_day[d][0],
                }
                for d in days_sorted
            ]
        )
    else:
        d0 = 0
        pdays = pd.DataFrame(columns=["day_index", "date", "tx", "laundering_tx", "laundering_share"])

    # post-period tail
    if primary_end_day is not None:
        R["primary_end"] = args.primary_end
        R["post_period_rows"] = tail_rows
        R["post_period_laundering_rows"] = tail_pos
        R["post_period_laundering_share"] = (tail_pos / tail_rows) if tail_rows else None

    # account-days
    A = np.concatenate(A_list) if A_list else np.array([], dtype="uint64")
    D = np.concatenate(D_list) if D_list else np.array([], dtype="int64")
    ua, ud, _ = group_or(A, D, np.zeros(len(A), dtype="uint8"))
    R["distinct_accounts_in_period"] = int(len(np.unique(ua)))
    R["account_days"] = int(len(ua))
    pa = np.concatenate(PA) if PA else np.array([], dtype="uint64")
    pdd = np.concatenate(PD) if PD else np.array([], dtype="int64")
    pr = np.concatenate(PR) if PR else np.array([], dtype="uint8")
    pua, pud, pur = group_or(pa, pdd, pr)
    R["positive_account_days"] = int(len(pua))
    R["positive_account_day_prevalence"] = len(pua) / max(len(ua), 1)
    R["accounts_touching_positives"] = int(len(np.unique(pua)))
    R["laundering_transactions_in_period"] = int(
        sum(v[1] for d, v in per_day.items() if primary_end_day is None or d <= primary_end_day)
    )
    if len(pua):
        R["positive_account_day_roles"] = {
            "sender_only": int((pur == 1).sum()),
            "receiver_only": int((pur == 2).sum()),
            "both": int((pur == 3).sum()),
        }
        same_next = (pua[1:] == pua[:-1]) & (pud[1:] == pud[:-1] + 1)
        R["label_persistence_next_day_share"] = float(same_next.sum() / len(pua))

    # account-day counts per day
    if len(ud):
        u, cnt = np.unique(ud, return_counts=True)
        ad_per_day = dict(zip(u.tolist(), cnt.tolist()))
    else:
        ad_per_day = {}
    if len(pud):
        u, cnt = np.unique(pud, return_counts=True)
        pad_per_day = dict(zip(u.tolist(), cnt.tolist()))
    else:
        pad_per_day = {}
    pdays["account_days"] = [ad_per_day.get(int(d0 + i - 1), 0) for i in pdays["day_index"]] if len(pdays) else []
    pdays["positive_account_days"] = (
        [pad_per_day.get(int(d0 + i - 1), 0) for i in pdays["day_index"]] if len(pdays) else []
    )

    # in-period day table (tail days excluded from every split / typology computation)
    if primary_end_day is not None and len(pdays):
        pdays_in = pdays[pdays["date"] <= args.primary_end]
    else:
        pdays_in = pdays

    # Definition B: non-overlapping k-day blocks
    k = args.block_days
    if len(ua):
        blk = (ud - ud.min()) // k
        ub_a, ub_d, _ = group_or(ua, blk, np.zeros(len(ua), dtype="uint8"))
        pblk = (pud - ud.min()) // k
        pb_a, pb_d, _ = group_or(pua, pblk, np.zeros(len(pua), dtype="uint8"))
        R["definition_B_block_days"] = k
        R["account_blocks"] = int(len(ub_a))
        R["positive_account_blocks"] = int(len(pb_a))
        R["review_cycles_definition_A_days"] = int(len(np.unique(ud)))
        R["review_cycles_definition_B_blocks"] = int(len(np.unique(blk)))

    # account -> bank stability
    if acct_bank_a:
        a = np.concatenate(acct_bank_a)
        b = np.concatenate(acct_bank_b)
        ua2, ub2, _ = group_or(a, b.view("int64"), np.zeros(len(a), dtype="uint8"))
        _, c = np.unique(ua2, return_counts=True)
        R["accounts_mapped_to_multiple_banks"] = int((c > 1).sum())

    # tail-only days (automatic detection even without --primary-end)
    if len(pdays) > 3:
        med = float(pdays["tx"].median())
        sus = pdays[(pdays["laundering_share"] >= 0.9) & (pdays["tx"] < 0.01 * med)]
        R["suspected_tail_days"] = sus["date"].tolist()

    # ---------------------------------------------------------------- typologies
    typ_table = pd.DataFrame()
    fam_table = pd.DataFrame()
    if typ_rows:
        tr = np.array(typ_rows, dtype=[("a", "uint64"), ("d", "int64"), ("t", "int64")])
        test_start = (pdays_in["day_index"].max() - args.test_days + 1) if len(pdays_in) else 0
        rows = []
        for ti, name in enumerate(typ_names):
            sel = tr[tr["t"] == ti]
            aa, dd, _ = group_or(sel["a"], sel["d"], np.zeros(len(sel), dtype="uint8"))
            di = dd - d0 + 1
            nblocks = sum(1 for b in blocks if b["typology"] == name) if blocks else None
            starts_test = (
                sum(1 for b in blocks if b["typology"] == name and b["day_min"] - d0 + 1 >= test_start)
                if blocks
                else None
            )
            rows.append(
                {
                    "typology": name,
                    "family": family_of(name),
                    "scheme_instances": nblocks,
                    "positive_account_days": int(len(aa)),
                    "unique_accounts": int(len(np.unique(aa))),
                    "pos_account_days_in_test_block": int((di >= test_start).sum()),
                    "scheme_starts_in_test_block": starts_test,
                }
            )
        typ_table = pd.DataFrame(rows)
        typ_table["coverage_of_positive_tx"] = np.nan
        if args.schema == "ibm" and blocks:
            cnt = Counter()
            for b in blocks:
                for k_ in set(b["keys"]):
                    if k_ in matched_keys:
                        cnt[b["typology"]] += 1
            typ_table["positive_tx_matched_unique"] = typ_table["typology"].map(cnt).fillna(0).astype(int)
            typ_table["coverage_of_positive_tx"] = typ_table["positive_tx_matched_unique"] / max(
                R["laundering_transactions_in_period"], 1
            )
        typ_table["suitable_overall"] = (typ_table["positive_account_days"] >= args.min_acct_days) & (
            typ_table["unique_accounts"] >= args.min_accounts
        )
        cond = (typ_table["pos_account_days_in_test_block"] >= args.min_acct_days) & (
            typ_table["unique_accounts"] >= args.min_accounts
        )
        if typ_table["scheme_starts_in_test_block"].notna().all():
            cond &= typ_table["scheme_starts_in_test_block"] >= args.min_instances
        typ_table["suitable_in_test_block(pre-declared rule)"] = cond
        fam_table = (
            typ_table.groupby("family")
            .agg(
                typologies=("typology", "count"),
                positive_account_days=("positive_account_days", "sum"),
                pos_account_days_in_test_block=("pos_account_days_in_test_block", "sum"),
            )
            .reset_index()
        )
        R["typed_positive_transactions"] = int(pos_tx_typed)
        R["untyped_positive_transactions"] = (
            int(R["laundering_transactions_in_period"] - pos_tx_typed) if args.schema == "ibm" else 0
        )
        R["typed_share_of_laundering_transactions"] = pos_tx_typed / max(R["laundering_transactions_in_period"], 1)
        R["positive_transactions_in_multiple_typologies"] = int(pos_tx_multi)
        R["unmapped_families"] = sorted(typ_table.loc[typ_table["family"] == "UNMAPPED", "typology"].tolist())

    if blocks:
        R["pattern_file"] = pat_info
        all_pattern_keys = {k_ for b in blocks for k_ in b["keys"]}
        R["pattern_transactions_unique"] = len(all_pattern_keys)
        R["pattern_transactions_not_found_in_main_csv"] = len(all_pattern_keys - matched_keys)
        span = [b["day_max"] - b["day_min"] + 1 for b in blocks if b["day_min"] >= 0]
        R["scheme_instances_total"] = len(blocks)
        R["share_schemes_spanning_gt1_day"] = float(np.mean([s > 1 for s in span])) if span else None
        cnt_acc = Counter(a for b in blocks for a in b["accounts"])
        R["share_pattern_accounts_in_multiple_schemes"] = (
            float(np.mean([v > 1 for v in cnt_acc.values()])) if cnt_acc else None
        )
        by_typ: dict[str, set] = {}
        for b in blocks:
            by_typ.setdefault(b["typology"], set()).update(b["accounts"])
        c2 = Counter(a for s in by_typ.values() for a in s)
        R["share_pattern_accounts_in_multiple_typologies"] = (
            float(np.mean([v > 1 for v in c2.values()])) if c2 else None
        )

    # ---------------------------------------------------------------- split feasibility
    feas = []
    if len(pdays_in):
        D_ = int(pdays_in["day_index"].max())
        starts = Counter()
        for b in blocks:
            if b["day_min"] >= 0:
                starts[int(b["day_min"] - d0 + 1)] += 1
        pad = {int(r.day_index): int(r.positive_account_days) for r in pdays_in.itertuples()}
        for T in range(1, D_ - (args.burn_in + args.val_days + args.purge + 1) + 1):
            t0 = D_ - T + 1
            v1 = t0 - args.purge - 1
            v0 = v1 - args.val_days + 1
            tr0, tr1 = args.burn_in + 1, v0 - 1
            if tr1 < tr0:
                continue
            tp = sum(pad.get(x, 0) for x in range(t0, D_ + 1))
            vp = sum(pad.get(x, 0) for x in range(v0, v1 + 1))
            trp = sum(pad.get(x, 0) for x in range(tr0, tr1 + 1))
            ss = sum(starts.get(x, 0) for x in range(t0, D_ + 1)) if blocks else None
            feas.append(
                {
                    "test_days": T,
                    "burn_in": f"1-{args.burn_in}",
                    "train": f"{tr0}-{tr1}",
                    "val": f"{v0}-{v1}",
                    "purge": f"{v1 + 1}-{t0 - 1}" if args.purge else "-",
                    "test": f"{t0}-{D_}",
                    "train_pos_acct_days": trp,
                    "val_pos_acct_days": vp,
                    "test_pos_acct_days": tp,
                    "test_scheme_starts": ss,
                    "resolution_halfwidth_pp(schemes, p=.5)": None
                    if ss is None
                    else round(100 * wilson_halfwidth(ss), 1),
                    "meets_min_test_pos_acct_days": tp >= args.min_acct_days,
                    "meets_min_test_schemes": (ss is None) or (ss >= args.min_instances),
                }
            )
    feas_df = pd.DataFrame(feas)
    R["distinct_days_in_period"] = int(len(pdays_in))

    # ---------------------------------------------------------------- warnings
    W = []
    if primary_end_day is None:
        W.append(
            "W_NO_PRIMARY_END: --primary-end not given; post-period rows (documented as all-laundering) are NOT excluded from account-days."
        )
    if R.get("post_period_rows"):
        W.append(
            f"W_TAIL: {R['post_period_rows']} rows after the primary period; laundering share {R['post_period_laundering_share']:.3f}. Exclude from cases; never use absolute time as a feature."
        )
    if R.get("suspected_tail_days"):
        W.append(f"W_TAILDAY: days with laundering share >= 0.9 and < 1% of median volume: {R['suspected_tail_days']}")
    if R.get("duplicate_rows"):
        W.append(f"W_DUP: {R['duplicate_rows']} fully duplicated rows (may be legitimate repeats; inspect).")
    if n_bad_ts:
        W.append(f"W_TS: {n_bad_ts} unparseable timestamps.")
    if R.get("accounts_mapped_to_multiple_banks"):
        W.append(
            f"W_ACCTBANK: {R['accounts_mapped_to_multiple_banks']} account IDs appear under more than one bank ID (ID stability)."
        )
    if n_selfloop:
        W.append(f"W_SELF: {n_selfloop} self-transfers (sender == receiver).")
    if R.get("pattern_transactions_not_found_in_main_csv"):
        W.append(
            f"W_PATTERN_MISMATCH: {R['pattern_transactions_not_found_in_main_csv']} pattern-file transactions were not found in the transactions file (key matching or format assumption may be wrong)."
        )
    if pos_tx_multi:
        W.append(f"W_PATTERN_OVERLAP: {pos_tx_multi} positive transactions belong to >1 typology.")
    if (
        R.get("typed_share_of_laundering_transactions") is not None
        and R["typed_share_of_laundering_transactions"] < 0.8
    ):
        W.append(
            f"W_COVERAGE: only {R['typed_share_of_laundering_transactions']:.1%} of laundering transactions carry a typology; untyped laundering must not be used as negatives in typology experiments."
        )
    if R.get("unmapped_families"):
        W.append(f"W_UNMAPPED_FAMILY: typologies not mapped to a structural family: {R['unmapped_families']}")
    if R.get("share_schemes_spanning_gt1_day") and R["share_schemes_spanning_gt1_day"] > 0.5:
        W.append("W_SCHEME_SPAN: >50% of schemes span more than one calendar day (day-boundary splitting).")
    if R.get("label_persistence_next_day_share", 0) > 0.6:
        W.append(
            "W_PERSIST: >60% of positive account-days have a positive next day (strong case dependence; use scheme clusters)."
        )
    if R.get("distinct_days_in_period", 99) < 14:
        W.append(
            f"W_FEW_DAYS: {R['distinct_days_in_period']} usable days; expanding-window multi-fold validation is not supported."
        )
    if args.schema == "samld":
        W.append("W_VERSION: pin SAML-D by file hash; published versions differ in size and prevalence.")
    R["warnings"] = W

    # ---------------------------------------------------------------- outputs
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pdays.to_csv(out / "per_day.csv", index=False)
    if len(typ_table):
        typ_table.to_csv(out / "typology_table.csv", index=False)
        fam_table.to_csv(out / "family_table.csv", index=False)
    if len(feas_df):
        feas_df.to_csv(out / "split_feasibility.csv", index=False)
    (out / "profile_report.json").write_text(
        json.dumps(R, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    )
    _write_markdown(out / "profile_report.md", R, typ_table, fam_table, feas_df, args)
    _plots(out, pdays, typ_table)
    return R


def _write_markdown(path: Path, R: dict, typ: pd.DataFrame, fam: pd.DataFrame, feas: pd.DataFrame, args) -> None:
    L = [
        f"# Profile report — {Path(args.transactions).name}",
        "",
        "Generated by `ml/profiling/profile_dataset.py` (Gate 0.5 instrument; no modelling). "
        "Numbers below are **file-level facts only if this was run on the real file**.",
        "",
    ]
    keys = [
        "rows",
        "date_min",
        "date_max",
        "distinct_days",
        "distinct_days_in_period",
        "laundering_transactions_all_rows",
        "laundering_prevalence_all_rows",
        "laundering_transactions_in_period",
        "post_period_rows",
        "post_period_laundering_rows",
        "post_period_laundering_share",
        "distinct_accounts_in_period",
        "accounts_touching_positives",
        "account_days",
        "positive_account_days",
        "positive_account_day_prevalence",
        "positive_account_day_roles",
        "label_persistence_next_day_share",
        "account_blocks",
        "positive_account_blocks",
        "review_cycles_definition_A_days",
        "review_cycles_definition_B_blocks",
        "duplicate_rows",
        "timestamp_unparseable",
        "self_loops",
        "accounts_mapped_to_multiple_banks",
        "typed_share_of_laundering_transactions",
        "scheme_instances_total",
        "share_schemes_spanning_gt1_day",
        "share_pattern_accounts_in_multiple_schemes",
        "share_pattern_accounts_in_multiple_typologies",
        "pattern_transactions_not_found_in_main_csv",
    ]
    L += ["## Summary", "", "| Item | Value |", "|---|---|"]
    for k in keys:
        if k in R:
            L.append(f"| {k} | {R[k]} |")
    L += ["", "## Warnings", ""] + ([f"- {w}" for w in R["warnings"]] or ["- none"])
    if len(typ):
        try:
            tbl = typ.to_markdown(index=False)
        except ImportError:  # tabulate not installed
            tbl = "```\n" + typ.to_string(index=False) + "\n```"
        L += ["", "## Typology table", "", tbl]
    if len(fam):
        L += ["", "## Family table", "", fam.to_string(index=False)]
    if len(feas):
        L += ["", "## Candidate temporal layouts (expanding, single test block)", "", feas.to_string(index=False)]
    path.write_text("\n".join(L))


def _plots(out: Path, pdays: pd.DataFrame, typ: pd.DataFrame) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # plotting is optional
        (out / "plots_skipped.txt").write_text(str(e))
        return
    if len(pdays):
        fig, ax = plt.subplots(2, 2, figsize=(11, 7))
        ax[0, 0].bar(pdays["day_index"], pdays["tx"])
        ax[0, 0].set_title("Transactions per day")
        ax[0, 1].bar(pdays["day_index"], pdays["laundering_tx"], color="C3")
        ax[0, 1].set_title("Laundering transactions per day")
        ax[1, 0].plot(pdays["day_index"], pdays["laundering_share"], marker="o")
        ax[1, 0].set_title("Laundering share per day")
        ax[1, 1].bar(pdays["day_index"], pdays["positive_account_days"], color="C1")
        ax[1, 1].set_title("Positive account-days per day")
        for a in ax.ravel():
            a.set_xlabel("day index")
        fig.tight_layout()
        fig.savefig(out / "temporal.png", dpi=120)
        plt.close(fig)
    if len(typ):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(typ["typology"], typ["positive_account_days"])
        ax.set_title("Positive account-days by typology")
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        fig.savefig(out / "typology.png", dpi=120)
        plt.close(fig)


def main(argv=None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--schema", choices=["ibm", "samld"], required=True)
    p.add_argument("--transactions", required=True)
    p.add_argument("--patterns", help="IBM *_Patterns.txt (optional)")
    p.add_argument(
        "--primary-end",
        help="last day of the documented primary period, YYYY-MM-DD "
        "(Small 2022-09-10, Medium 2022-09-16, Large 2022-11-05)",
    )
    p.add_argument("--out", default="artifacts/profiling/run")
    p.add_argument("--chunksize", type=int, default=1_000_000)
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--block-days", type=int, default=3)
    p.add_argument("--burn-in", type=int, default=2)
    p.add_argument("--val-days", type=int, default=1)
    p.add_argument("--purge", type=int, default=1)
    p.add_argument("--test-days", type=int, default=5)
    p.add_argument("--min-acct-days", type=int, default=200)
    p.add_argument("--min-accounts", type=int, default=50)
    p.add_argument("--min-instances", type=int, default=30)
    p.add_argument("--skip-duplicates", action="store_true", help="save memory on very large files")
    args = p.parse_args(argv)
    R = profile(args)
    print(f"[OK] wrote {args.out}/profile_report.md ; warnings: {len(R['warnings'])}")
    return R


if __name__ == "__main__":
    main()
