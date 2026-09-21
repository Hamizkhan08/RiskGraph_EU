"""Metrics reflecting the research problem: ranking under capacity, calibration, workload.
Accuracy is intentionally absent; F1 is provided only for comparability."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, precision_recall_curve


def pr_auc(y: np.ndarray, s: np.ndarray) -> float:
    return float(average_precision_score(y, s)) if y.sum() > 0 else float("nan")


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(brier_score_loss(y, np.clip(p, 0, 1)))


def calibration_bins(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> list[dict]:
    """Quantile-binned reliability table (mean predicted vs observed rate)."""
    order = np.argsort(p, kind="stable")
    out = []
    for chunk in np.array_split(order, n_bins):
        if len(chunk):
            out.append(
                {
                    "mean_pred": float(p[chunk].mean()),
                    "obs_rate": float(y[chunk].mean()),
                    "n": int(len(chunk)),
                    "n_pos": int(y[chunk].sum()),
                }
            )
    return out


def ece(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    bins = calibration_bins(y, p, n_bins)
    n = sum(b["n"] for b in bins)
    return float(sum(b["n"] * abs(b["mean_pred"] - b["obs_rate"]) for b in bins) / max(n, 1))


def pr_curve_points(y: np.ndarray, s: np.ndarray, max_points: int = 100) -> list[dict]:
    p, r, _ = precision_recall_curve(y, s)
    idx = np.unique(np.linspace(0, len(p) - 1, min(max_points, len(p))).astype(int))
    return [{"recall": float(r[i]), "precision": float(p[i])} for i in idx]


def f1_at_review(y: np.ndarray, reviewed: np.ndarray) -> float:
    return float(f1_score(y, reviewed.astype(int), zero_division=0))


def daily_topk_mask(day: np.ndarray, score: np.ndarray, r: float) -> np.ndarray:
    """REVIEW flags: per day the top K_d = ceil(r * n_d) cases by score (stable tie-break)."""
    order = np.lexsort((np.arange(len(day)), -score, day))
    d_sorted = day[order]
    _, start, counts = np.unique(d_sorted, return_index=True, return_counts=True)
    rank = np.arange(len(day)) - np.repeat(start, counts)
    k = np.ceil(r * np.repeat(counts, counts)).astype(int)
    m = np.zeros(len(day), dtype=bool)
    m[order] = rank < k
    return m


def topk_summary(day: np.ndarray, score: np.ndarray, y: np.ndarray, r: float) -> dict:
    m = daily_topk_mask(day, score, r)
    tp = int((m & (y == 1)).sum())
    n_pos, n_rev = int(y.sum()), int(m.sum())
    prev = n_pos / max(len(y), 1)
    prec = tp / max(n_rev, 1)
    return {
        "r": float(r),
        "n_review": n_rev,
        "tp": tp,
        "recall": tp / max(n_pos, 1),
        "precision": prec,
        "lift": prec / prev if prev > 0 else float("nan"),
        "n_pos": n_pos,
        "n_cases": int(len(y)),
        "avg_k_per_day": n_rev / max(len(np.unique(day)), 1),
    }


def cluster_bootstrap_recall(
    cluster: np.ndarray,
    y: np.ndarray,
    reviewed_a: np.ndarray,
    reviewed_b: np.ndarray | None = None,
    n_boot: int = 500,
    seed: int = 0,
) -> dict:
    """Recall with scheme-cluster resampling (positives only); paired difference if `reviewed_b` given.

    The review set is FIXED (negatives are abundant, so the per-day cut is stable); only positive
    clusters are resampled. Cases with no scheme are treated as singleton clusters.
    """
    pos = y == 1
    if not pos.any():
        return {"recall": float("nan")}
    cl = cluster[pos].copy()
    singles = cl < 0
    cl[singles] = -1 - np.arange(int(singles.sum()))
    ids, inv = np.unique(cl, return_inverse=True)
    den = np.bincount(inv, minlength=len(ids)).astype(float)
    na = np.bincount(inv, weights=reviewed_a[pos].astype(float), minlength=len(ids))
    nb = np.bincount(inv, weights=reviewed_b[pos].astype(float), minlength=len(ids)) if reviewed_b is not None else None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ids), size=(n_boot, len(ids)))
    ra = na[idx].sum(1) / np.maximum(den[idx].sum(1), 1)
    out = {
        "recall": float(na.sum() / den.sum()),
        "ci95": [float(np.percentile(ra, 2.5)), float(np.percentile(ra, 97.5))],
        "n_clusters": int(len(ids)),
        "n_pos": int(den.sum()),
    }
    if nb is not None:
        rb = nb[idx].sum(1) / np.maximum(den[idx].sum(1), 1)
        d = ra - rb
        out.update(
            {
                "recall_b": float(nb.sum() / den.sum()),
                "diff": float(na.sum() / den.sum() - nb.sum() / den.sum()),
                "diff_ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            }
        )
    return out
