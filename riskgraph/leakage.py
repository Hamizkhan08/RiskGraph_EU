"""Automated leakage checks (also exercised by tests/test_leakage.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data.schema import TxData
from .features.build import CaseTable, build_cases
from .split import Split, block_mask, carry_over

FORBIDDEN_SUBSTRINGS = ("label", "fraud", "scheme", "family", "typology", "pattern", "risk_score", "is_", "target")


def forbidden_feature_names(cols: list[str]) -> list[str]:
    return [c for c in cols if any(s in c.lower() for s in FORBIDDEN_SUBSTRINGS)]


def _align(a: CaseTable, b: CaseTable, max_day: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    ka = pd.MultiIndex.from_arrays([a.acct, a.day])
    kb = pd.MultiIndex.from_arrays([b.acct, b.day])
    Xa = a.X.set_axis(ka)
    Xb = b.X.set_axis(kb)
    keep = [k for k in Xa.index if k[1] <= max_day]
    return Xa.loc[keep].sort_index(), Xb.loc[keep].sort_index()


def future_perturbation_check(td: TxData, cutoff_day: int, builder=build_cases) -> dict:
    """Features at day <= cutoff must be identical whether or not later transactions exist.

    `builder` is injectable so tests can prove the check FAILS on a deliberately leaky builder."""
    full = builder(td)
    cut = builder(td, max_day=cutoff_day)
    Xa, Xb = _align(full, cut, cutoff_day)
    diff = float(np.max(np.abs(Xa.to_numpy() - Xb.to_numpy()))) if len(Xa) else 0.0
    return {"cases_compared": int(len(Xa)), "max_abs_diff": diff, "ok": bool(diff < 1e-3 and len(Xa) == len(Xb))}


def label_independence_check(td: TxData, builder=build_cases) -> dict:
    """Features must be identical when every label / scheme / family field is destroyed."""
    base = builder(td)
    tx2 = td.tx.copy()
    tx2["y"], tx2["scheme_idx"], tx2["family_idx"] = 0, -1, -1
    td2 = TxData(
        tx=tx2,
        accounts=td.accounts,
        schemes=td.schemes.iloc[0:0],
        families=td.families,
        n_days=td.n_days,
        start_date=td.start_date,
        meta=td.meta,
    )
    other = builder(td2)
    same_shape = base.X.shape == other.X.shape
    diff = float(np.max(np.abs(base.X.to_numpy() - other.X.to_numpy()))) if same_shape else float("inf")
    return {"max_abs_diff": diff, "ok": bool(same_shape and diff == 0.0)}


def split_integrity(ct: CaseTable, sp: Split) -> dict:
    """Blocks disjoint and ordered; strict view leaves no carry-over positives."""
    blocks = {b: block_mask(ct, sp, b) for b in ("train", "val", "test")}
    overlap = int(sum((blocks[a] & blocks[b]).sum() for a, b in (("train", "val"), ("train", "test"), ("val", "test"))))
    ordered = sp.train[1] <= sp.val[0] and sp.val[1] <= sp.purge[0] and sp.purge[1] <= sp.test[0]
    strict_ok = True
    for b in ("val", "test"):
        m = blocks[b] & ~carry_over(ct, sp.block_range(b)[0])
        strict_ok &= not bool(((ct.y[m] == 1) & (ct.scheme_max_start[m] < sp.block_range(b)[0])).any())
    return {
        "overlap_cases": overlap,
        "ordered": bool(ordered),
        "strict_view_clean": bool(strict_ok),
        "ok": bool(overlap == 0 and ordered and strict_ok),
    }
