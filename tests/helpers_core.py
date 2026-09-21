"""Shared test helpers (core package)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from riskgraph.data.schema import TxData


def make_txdata(rows, n_days=40, accounts=("A", "B", "C", "D")) -> TxData:
    """rows: (day, hour, src, dst, amount, tx_type, currency, y)"""
    start = pd.Timestamp("2025-01-01")
    acc = np.array([f"account_{a}" for a in accounts])
    df = pd.DataFrame(rows, columns=["day", "hour", "s", "t", "amount", "tx_type", "currency", "y"])
    tx = pd.DataFrame(
        {
            "ts": (start + pd.to_timedelta(df["day"], unit="D") + pd.to_timedelta(df["hour"], unit="h")).dt.as_unit(
                "ns"
            ),
            "src": [f"account_{a}" for a in df["s"]],
            "dst": [f"account_{a}" for a in df["t"]],
            "amount": df["amount"].astype(float),
            "currency": df["currency"].astype("category"),
            "tx_type": df["tx_type"].astype("category"),
            "y": df["y"].astype("int8"),
        }
    )
    idx = pd.Index(acc)
    tx["src_idx"], tx["dst_idx"] = (
        idx.get_indexer(tx["src"]).astype("int32"),
        idx.get_indexer(tx["dst"]).astype("int32"),
    )
    tx["scheme_idx"], tx["family_idx"] = np.int32(-1), np.int16(-1)
    tx["day"] = df["day"].astype("int32").to_numpy()
    tx["in_period"] = tx["day"] < n_days
    tx = tx.sort_values("ts", kind="stable").reset_index(drop=True)
    schemes = pd.DataFrame({c: pd.Series(dtype="float64") for c in ("scheme_idx", "family_idx", "start_day")})
    return TxData(
        tx=tx,
        accounts=acc,
        schemes=schemes,
        families=["f0"],
        n_days=n_days,
        start_date=start,
        meta={"name": "hand-built"},
    )
