import json

import pandas as pd
import pytest

from riskgraph.data.amlnet import load_amlnet
from riskgraph.data.schema import validate_transactions
from riskgraph.data.tide import load_tide

HEADER = (
    "src,dest,edge_type,amount,currency,is_fraudulent,ownership_percentage,ownership_start_date,"
    "time_since_previous_transaction,timestamp,transaction_type\n"
)


def _tide_dir(tmp_path):
    rows = [
        "account_1,account_2,transaction,20.5,EUR,False,100.0,2025-01-01,0:01:00,2025-01-05 10:00:00,TransactionType.PAYMENT",
        "account_1,account_3,transaction,500.0,EUR,True,100.0,2025-01-01,0:01:00,2025-01-10 10:00:00,TransactionType.TRANSFER",
        "account_3,account_4,transaction,480.5,GBP,True,100.0,2025-01-01,0:01:00,2025-01-11 09:30:00.500000,TransactionType.TRANSFER",
        "individual_9,account_4,transaction,900.0,EUR,True,100.0,2025-01-01,0:01:00,2025-01-12 08:00:00,TransactionType.DEPOSIT",
        "account_4,account_1,transaction,300.0,EUR,True,100.0,2025-01-01,0:01:00,2025-02-05 08:00:00,TransactionType.TRANSFER",
    ]
    (tmp_path / "generated_transactions.csv").write_text(HEADER + "\n".join(rows) + "\n")
    tx = [
        ("account_1", "account_3", 500.0, "2025-01-10 10:00:00", "TransactionType.TRANSFER", "EUR"),
        ("account_3", "account_4", 480.5, "2025-01-11 09:30:00.500000", "TransactionType.TRANSFER", "GBP"),
        ("individual_9", "account_4", 900.0, "2025-01-12 08:00:00", "TransactionType.DEPOSIT", "EUR"),
        ("account_4", "account_1", 300.0, "2025-02-05 08:00:00", "TransactionType.TRANSFER", "EUR"),
    ]
    pats = {
        "metadata": {},
        "patterns": [
            {
                "pattern_type": "UTurnTransactions",
                "pattern_id": "UTurnTransactions_1",
                "transactions": [
                    dict(src=a, dest=b, amount=c, timestamp=d, transaction_type=e, currency=f)
                    for a, b, c, d, e, f in tx
                ],
            }
        ],
    }
    (tmp_path / "generated_patterns.json").write_text(json.dumps(pats))
    (tmp_path / "dataset_meta.json").write_text(
        json.dumps({"name": "t", "start_date": "2025-01-01", "period_days": 30})
    )
    return tmp_path


def test_tide_adapter_labels_schemes_and_tail(tmp_path):
    td = load_tide(_tide_dir(tmp_path))
    assert td.families == ["UTurnTransactions"] and td.n_days == 30
    assert int(td.tx["y"].sum()) == 4 and (td.tx.loc[td.tx.y == 1, "scheme_idx"] == 0).all()
    assert int(td.tx["in_period"].sum()) == 4  # Feb row is after the 30-day period
    assert td.tx["src_idx"].min() == -1  # individual endpoint is not an account
    assert set(td.accounts) == {"account_1", "account_2", "account_3", "account_4"}
    s = td.schemes.iloc[0]
    assert s["start_day"] == 9 and s["family_idx"] == 0
    rep = validate_transactions(td)
    assert rep["post_period_rows"] == 1 and rep["post_period_positive_share"] == 1.0
    assert any("W_TAIL" in w for w in rep["warnings"])
    assert "generated_nodes.csv (all)" in td.meta["excluded_columns"]
    assert len(td.meta["files_sha256"]["generated_transactions.csv"]) == 64


def test_tide_adapter_fails_loudly_without_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_tide(tmp_path)


def test_validation_rejects_unsorted(fixture_td):
    bad = fixture_td.tx.iloc[::-1].reset_index(drop=True)
    from riskgraph.data.schema import TxData

    td = TxData(
        tx=bad,
        accounts=fixture_td.accounts,
        schemes=fixture_td.schemes,
        families=fixture_td.families,
        n_days=fixture_td.n_days,
        start_date=fixture_td.start_date,
        meta={"name": "bad"},
    )
    with pytest.raises(ValueError, match="sorted"):
        validate_transactions(td)


def test_fixture_validates_and_is_labelled_synthetic(fixture_td):
    rep = validate_transactions(fixture_td)
    assert rep["duplicate_rows"] == 0 and rep["nonpositive_amounts"] == 0
    assert "SYNTHETIC" in fixture_td.meta["source_note"].upper()
    assert rep["schemes_total"] == 27


def test_amlnet_adapter_on_documented_schema(tmp_path):
    n = 6
    df = pd.DataFrame(
        {
            "step": range(n),
            "type": ["PAYMENT", "TRANSFER"] * 3,
            "amount": [10.0, 200.0, 30.0, 4000.0, 5.0, 60.0],
            "nameOrig": ["C1", "C2", "C1", "C3", "C2", "C1"],
            "nameDest": ["M1", "C1", "M2", "C2", "M1", "C3"],
            "oldbalanceOrg": 1.0,
            "newbalanceOrig": 1.0,
            "isFraud": 0,
            "isMoneyLaundering": [0, 1, 0, 1, 0, 0],
            "laundering_typology": ["normal", "structuring", "normal", "layering", "normal", "normal"],
            "fraud_probability": 0.9,
            "hour": range(n),
            "day_of_week": 1,
            "day_of_month": [13, 13, 14, 14, 15, 15],
            "month": 10,
            "metadata": [json.dumps({"timestamp": f"2025-10-{13 + i // 2} 0{i}:00:00"}) for i in range(n)],
        }
    )
    p = tmp_path / "amlnet.csv"
    df.to_csv(p, index=False)
    td = load_amlnet(p)
    assert td.families == ["structuring", "layering", "integration"]
    assert int(td.tx["y"].sum()) == 2 and set(td.tx.loc[td.tx.y == 1, "family_idx"]) == {0, 1}
    assert td.meta["scheme_ids_available"] is False
    assert "fraud_probability" not in td.tx.columns and "fraud_probability" in td.meta["excluded_columns"]
    assert td.n_days == 3
    with pytest.raises(ValueError, match="missing documented columns"):
        load_amlnet(_write_bad(tmp_path))


def _write_bad(tmp_path):
    p = tmp_path / "bad.csv"
    pd.DataFrame({"a": [1]}).to_csv(p, index=False)
    return p
