"""Model-grounded explanations. Every number shown to an analyst comes from the model or the data.

  * LightGBM: exact TreeSHAP via LightGBM's built-in `pred_contrib` (log-odds space).
  * Logistic regression: exact linear attribution (coef x standardised, transformed value).
  * Reason codes group features; they add no information beyond the attributions.
  * Evidence = actual transactions/edges available at the decision timestamp (end of day d).
LLM text is never a source of truth (no LLM is used in this build)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .data.schema import TxData
from .features.build import FEATURES
from .reasons import REASON_LABELS, reason_code  # noqa: F401


def contributions(model: Any, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(contrib [n, F], base [n]) in log-odds; contrib.sum(1)+base == raw margin."""
    A = X[model.cols].to_numpy()
    if model.kind == "lgbm":
        c = model.est.booster_.predict(A, pred_contrib=True)
        return c[:, :-1], c[:, -1]
    from .models import _slog

    pipe = model.est
    Z = pipe.named_steps["scale"].transform(_slog(A))
    lr = pipe.named_steps["lr"]
    return Z * lr.coef_[0], np.full(len(A), float(lr.intercept_[0]))


def explain_rows(model: Any, X: pd.DataFrame, top: int = 6) -> list[dict]:
    C, base = contributions(model, X)
    vals = X[model.cols].to_numpy()
    out = []
    for i in range(len(X)):
        order = np.argsort(-np.abs(C[i]))[:top]
        feats = [
            {
                "feature": model.cols[j],
                "value": float(vals[i, j]),
                "contribution": float(C[i, j]),
                "group": FEATURES[model.cols[j]][0],
                "definition": FEATURES[model.cols[j]][1],
                "reason_code": reason_code(model.cols[j]),
            }
            for j in order
        ]
        grouped: dict[str, float] = {}
        for j, f in enumerate(model.cols):
            grouped[reason_code(f)] = grouped.get(reason_code(f), 0.0) + float(C[i, j])
        reasons = [
            {"code": k, "label": REASON_LABELS[k], "contribution": v}
            for k, v in sorted(grouped.items(), key=lambda kv: -abs(kv[1]))[:4]
        ]
        out.append(
            {
                "base_value": float(base[i]),
                "margin": float(base[i] + C[i].sum()),
                "top_features": feats,
                "reasons": reasons,
            }
        )
    return out


def case_evidence(
    td: TxData, acct_idx: int, day: int, lookback: int = 7, max_tx: int = 15, max_nodes: int = 24
) -> dict:
    """Evidence available at the decision timestamp: transactions with day in (day-lookback, day]."""
    tx = td.tx
    m = tx["in_period"].to_numpy() & (tx["day"].to_numpy() <= day) & (tx["day"].to_numpy() > day - lookback)
    inv = m & ((tx["src_idx"].to_numpy() == acct_idx) | (tx["dst_idx"].to_numpy() == acct_idx))
    mine = tx[inv]
    focal = str(td.accounts[acct_idx])
    rows = mine.sort_values("amount", ascending=False).head(max_tx)
    txs = [
        {
            "timestamp": r.ts.isoformat(),
            "src": r.src,
            "dst": r.dst,
            "amount": float(r.amount),
            "currency": str(r.currency),
            "type": str(r.tx_type),
            "direction": "out" if r.src == focal else "in",
        }
        for r in rows.itertuples()
    ]
    cp = pd.concat([mine.assign(cp=mine["dst"], out=1), mine.assign(cp=mine["src"], out=0)])
    cp = cp[cp["cp"] != focal]
    g = (
        cp.groupby("cp")
        .agg(n=("amount", "size"), amount=("amount", "sum"), n_out=("out", "sum"))
        .sort_values("amount", ascending=False)
    )
    top_cp = list(g.head(max_nodes - 1).index)
    nodes = [{"id": focal, "focal": True, "n": int(len(mine)), "amount": float(mine["amount"].sum())}]
    nodes += [{"id": c, "focal": False, "n": int(g.loc[c, "n"]), "amount": float(g.loc[c, "amount"])} for c in top_cp]
    keep = set(top_cp) | {focal}
    win = tx[m & tx["src"].isin(keep).to_numpy() & tx["dst"].isin(keep).to_numpy()]
    e = (
        win.groupby(["src", "dst"])
        .agg(n=("amount", "size"), amount=("amount", "sum"), first=("ts", "min"), last=("ts", "max"))
        .reset_index()
    )
    edges = [
        {
            "source": r["src"],
            "target": r["dst"],
            "n": int(r["n"]),
            "amount": float(r["amount"]),
            "first": pd.Timestamp(r["first"]).isoformat(),
            "last": pd.Timestamp(r["last"]).isoformat(),
        }
        for r in e.to_dict("records")
    ]
    return {
        "focal": focal,
        "decision_timestamp": str((td.start_date + pd.Timedelta(days=int(day) + 1)).isoformat()),
        "lookback_days": lookback,
        "transactions": txs,
        "n_transactions_window": int(len(mine)),
        "counterparties_total": int(len(g)),
        "nodes": nodes,
        "edges": edges,
    }
