"""Tests for ml/profiling/profile_dataset.py on a SYNTHETIC fixture.

The fixture is invented data with planted properties (a post-period all-laundering tail, a
duplicate row, a malformed timestamp, an account under two banks, a self-loop, three pattern
blocks, untyped laundering). Expected values are computed INDEPENDENTLY in this file with plain
pandas, so the profiler is checked against a second implementation.

Nothing here says anything about the real IBM or SAML-D files. In particular the pattern-file
format is an ASSUMPTION; only the real file can confirm it.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml" / "profiling"))
import profile_dataset as P  # noqa: E402

HEADER = (
    "Timestamp,From Bank,Account,To Bank,Account,Amount Received,Receiving Currency,"
    "Amount Paid,Payment Currency,Payment Format,Is Laundering"
)


def acct(n: int) -> str:
    return f"8{n:04X}"


def bank(n: int) -> str:
    return f"{10 + n % 5:03d}"


def row(ts, s, d, y, amt=100.0, cur="US Dollar", fmt="ACH", sb=None, db=None):
    sb = bank(s) if sb is None else sb
    db = bank(d) if db is None else db
    return f"{ts},{sb},{acct(s)},{db},{acct(d)},{amt},{cur},{amt},{cur},{fmt},{y}"


def build(tmp: Path):
    rng = np.random.default_rng(7)
    rows, meta = [], []  # meta: (day, src, dst, y) for rows with a valid timestamp

    def add(ts, s, d, y, **kw):
        rows.append(row(ts, s, d, y, **kw))
        day = int(ts[8:10]) if ts[:4] == "2022" and ts[5:7] == "09" and len(ts) == 16 else None
        meta.append((day, acct(s), acct(d), y))

    # normal traffic, days 1-10
    for _ in range(6000):
        s, d = rng.integers(0, 300, 2)
        if s == d:
            continue
        day = int(rng.integers(1, 11))
        add(
            f"2022/09/{day:02d} {int(rng.integers(0, 24)):02d}:{int(rng.integers(0, 60)):02d}",
            s,
            d,
            0,
            amt=float(rng.integers(10, 5000)),
        )

    blocks = []
    # FAN-OUT: day 3, 4 tx
    b = [(f"2022/09/03 10:0{i}", 250, 260 + i) for i in range(4)]
    blocks.append(("FAN-OUT", b))
    # CYCLE: day 4, 3 tx
    b = [("2022/09/04 09:00", 270, 271), ("2022/09/04 09:05", 271, 272), ("2022/09/04 09:10", 272, 270)]
    blocks.append(("CYCLE", b))
    # SCATTER-GATHER: spans day 5 -> day 6, 6 tx
    b = [
        ("2022/09/05 23:58", 280, 281),
        ("2022/09/05 23:59", 280, 282),
        ("2022/09/05 23:59", 280, 283),
        ("2022/09/06 00:01", 281, 290),
        ("2022/09/06 00:02", 282, 290),
        ("2022/09/06 00:03", 283, 290),
    ]
    blocks.append(("SCATTER-GATHER", b))
    for _, b in blocks:
        for ts, s, d in b:
            add(ts, s, d, 1)
    # untyped laundering: day 7, 5 tx
    for i in range(5):
        add(f"2022/09/07 12:0{i}", 295, 296 + i % 3, 1)
    # post-period tail (days 11-12): 30 tx, all laundering
    for i in range(30):
        add(f"2022/09/{11 + i % 2:02d} 08:{i:02d}", 200 + i % 10, 210 + i % 7, 1)
    # planted data-quality defects
    rows.append(rows[10])  # exact duplicate row
    meta.append(meta[10])
    rows.append(row("not-a-date", 1, 2, 0))  # malformed timestamp
    meta.append((None, acct(1), acct(2), 0))
    add("2022/09/02 11:11", 5, 5, 0)  # self-loop
    add("2022/09/02 11:12", 40, 41, 0, sb="010", db="011")  # same account under two banks:
    add("2022/09/02 11:13", 41, 40, 0, sb="012", db="010")  # 41 appears as 011 and 012

    tx = tmp / "toy_Trans.csv"
    tx.write_text(HEADER + "\n" + "\n".join(rows) + "\n")

    lines = []
    for name, b in blocks:
        lines.append(f"BEGIN LAUNDERING ATTEMPT - {name}:  synthetic")
        for ts, s, d in b:
            lines.append(row(ts, s, d, 1))
        lines.append(f"END LAUNDERING ATTEMPT - {name}")
        lines.append("")
    pat = tmp / "toy_Patterns.txt"
    pat.write_text("\n".join(lines))
    return tx, pat, blocks, meta


def expected_account_days(meta, tail_from=11):
    m = pd.DataFrame(meta, columns=["day", "s", "d", "y"]).dropna(subset=["day"])
    m = m[m["day"] < tail_from]
    ends = pd.concat([m[["day", "s", "y"]].rename(columns={"s": "a"}), m[["day", "d", "y"]].rename(columns={"d": "a"})])
    all_ad = ends[["a", "day"]].drop_duplicates()
    pos_ad = ends[ends["y"] == 1][["a", "day"]].drop_duplicates()
    return len(all_ad), len(pos_ad), pos_ad


def run(tmp_path):
    tx, pat, blocks, meta = build(tmp_path)
    out = tmp_path / "out"
    R = P.main(
        [
            "--schema",
            "ibm",
            "--transactions",
            str(tx),
            "--patterns",
            str(pat),
            "--primary-end",
            "2022-09-10",
            "--out",
            str(out),
            "--chunksize",
            "1500",
            "--test-days",
            "3",
            "--min-acct-days",
            "5",
            "--min-accounts",
            "3",
            "--min-instances",
            "1",
        ]
    )
    return R, out, blocks, meta


def test_counts_tail_and_defects(tmp_path):
    R, out, blocks, meta = run(tmp_path)
    assert R["timestamp_unparseable"] == 1
    assert R["duplicate_rows"] >= 1
    assert R["self_loops"] == 1
    assert R["accounts_mapped_to_multiple_banks"] >= 1
    # laundering: 13 typed + 5 untyped in period, 30 in the tail, all rows = 48
    assert R["laundering_transactions_all_rows"] == 48
    assert R["laundering_transactions_in_period"] == 18
    assert R["post_period_rows"] == 30 and R["post_period_laundering_rows"] == 30
    assert R["post_period_laundering_share"] == 1.0
    assert any(w.startswith("W_TAIL") for w in R["warnings"])
    assert any(w.startswith("W_DUP") for w in R["warnings"])
    assert any(w.startswith("W_TS") for w in R["warnings"])


def test_account_days_match_independent_computation(tmp_path):
    R, out, blocks, meta = run(tmp_path)
    n_all, n_pos, pos_ad = expected_account_days(meta)
    assert R["account_days"] == n_all
    assert R["positive_account_days"] == n_pos
    # role split: an account that only receives vs only sends vs both, on the same day
    m = pd.DataFrame(meta, columns=["day", "s", "d", "y"]).dropna(subset=["day"])
    m = m[(m["day"] < 11) & (m["y"] == 1)]
    s_ad = set(zip(m["s"], m["day"]))
    d_ad = set(zip(m["d"], m["day"]))
    both = len(s_ad & d_ad)
    assert R["positive_account_day_roles"]["both"] == both
    assert R["positive_account_day_roles"]["sender_only"] == len(s_ad - d_ad)
    assert R["positive_account_day_roles"]["receiver_only"] == len(d_ad - s_ad)


def test_pattern_parsing_and_coverage(tmp_path):
    R, out, blocks, meta = run(tmp_path)
    assert R["scheme_instances_total"] == 3
    assert R["pattern_transactions_not_found_in_main_csv"] == 0
    assert R["typed_positive_transactions"] == 13
    assert R["untyped_positive_transactions"] == 5
    assert abs(R["typed_share_of_laundering_transactions"] - 13 / 18) < 1e-9
    assert abs(R["share_schemes_spanning_gt1_day"] - 1 / 3) < 1e-9  # only SCATTER-GATHER crosses midnight
    typ = pd.read_csv(out / "typology_table.csv").set_index("typology")
    assert set(typ.index) == {"FAN-OUT", "CYCLE", "SCATTER-GATHER"}
    assert typ.loc["FAN-OUT", "family"] == "F1_fan"
    assert typ.loc["SCATTER-GATHER", "family"] == "F1_fan"  # shares fan motifs
    assert typ.loc["CYCLE", "family"] == "F2_cycle"
    # independent expectation for the CYCLE block: accounts 270,271,272 on day 4 -> 3 account-days
    assert typ.loc["CYCLE", "positive_account_days"] == 3
    assert typ.loc["CYCLE", "unique_accounts"] == 3
    # FAN-OUT: source + 4 targets on day 3 -> 5 account-days
    assert typ.loc["FAN-OUT", "positive_account_days"] == 5


def test_outputs_exist_and_split_table_excludes_tail(tmp_path):
    R, out, blocks, meta = run(tmp_path)
    for f in [
        "profile_report.json",
        "profile_report.md",
        "per_day.csv",
        "typology_table.csv",
        "family_table.csv",
        "split_feasibility.csv",
    ]:
        assert (out / f).exists(), f
    feas = pd.read_csv(out / "split_feasibility.csv")
    # 10 in-period days; layout needs burn-in 2 + val 1 + purge 1 + >=1 train -> test_days <= 5
    assert feas["test_days"].max() == 5
    assert all(int(x.split("-")[1]) <= 10 for x in feas["test"])  # tail days 11-12 never used
    assert R["distinct_days_in_period"] == 10


def test_family_rules():
    assert P.family_of("FAN-OUT") == "F1_fan"
    assert P.family_of("Fan-In") == "F1_fan"
    assert P.family_of("GATHER-SCATTER") == "F1_fan"
    assert P.family_of("SIMPLE CYCLE") == "F2_cycle"
    assert P.family_of("STACK") == "F3_biclique"
    assert P.family_of("SOMETHING NEW") == "UNMAPPED"


def test_wrong_header_fails_loudly(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b,c\n1,2,3\n")
    try:
        P.main(["--schema", "ibm", "--transactions", str(bad), "--out", str(tmp_path / "o")])
    except SystemExit as e:
        assert "IBM header differs" in str(e)
    else:
        raise AssertionError("expected SystemExit")


def test_samld_branch_typology_from_column(tmp_path):
    """SAML-D schema: typology comes from the Laundering_type column (column names per the paper and
    a 2026 paper's usage; exact names in the real file are UNVERIFIED and the profiler fails loudly if
    they differ)."""
    hdr = (
        "Time,Date,Sender_account,Receiver_account,Amount,Payment_currency,Received_currency,"
        "Sender_bank_location,Receiver_bank_location,Payment_type,Is_laundering,Laundering_type"
    )
    rng = np.random.default_rng(3)
    rows = []
    for _ in range(2000):
        s, d = rng.integers(0, 100, 2)
        if s == d:
            continue
        day = int(rng.integers(1, 9))
        rows.append(
            f"10:00:00,2023-01-{day:02d},{1000 + s},{1000 + d},50.0,UK pounds,UK pounds,UK,UK,ACH,0,Normal_Small_Fan_Out"
        )
    # 2 suspicious typologies on day 8: 3 + 2 transactions
    for i in range(3):
        rows.append(
            f"11:0{i}:00,2023-01-08,{2000 + i},{2100},900.0,UK pounds,Euro,UK,Mexico,Cross-border,1,Structuring"
        )
    for i in range(2):
        rows.append(f"12:0{i}:00,2023-01-08,{2200},{2300 + i},900.0,UK pounds,UK pounds,UK,UK,Cash Deposit,1,Smurfing")
    tx = tmp_path / "samld_toy.csv"
    tx.write_text(hdr + "\n" + "\n".join(rows) + "\n")
    R = P.main(
        [
            "--schema",
            "samld",
            "--transactions",
            str(tx),
            "--out",
            str(tmp_path / "o2"),
            "--test-days",
            "2",
            "--min-acct-days",
            "1",
            "--min-accounts",
            "1",
        ]
    )
    assert R["laundering_transactions_all_rows"] == 5
    typ = pd.read_csv(tmp_path / "o2" / "typology_table.csv").set_index("typology")
    assert set(typ.index) == {"STRUCTURING", "SMURFING"}
    # Structuring: senders 2000..2002 + receiver 2100 = 4 account-days; Smurfing: sender 2200 + receivers 2300,2301 = 3
    assert typ.loc["STRUCTURING", "positive_account_days"] == 4
    assert typ.loc["SMURFING", "positive_account_days"] == 3
    assert any(w.startswith("W_VERSION") for w in R["warnings"])
