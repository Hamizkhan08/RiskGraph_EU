"""Capacity-constrained decision engine.

Zones (mutually exclusive, exhaustive over the pool of a day; precedence REVIEW > AUTO-CLOSE > BACKLOG):
    pool_d = new cases of day d  U  pending backlog
    REVIEW     : top K_d of pool_d by score, K_d = ceil(r * |new_d|)            (r = m * train prevalence)
    AUTO-CLOSE : among the rest, score <= tau_d                                  ("safe" by policy)
    BACKLOG    : the rest (age + 1); cases older than M days EXPIRE unreviewed   (a miss if positive)

tau_d comes from the policy, using only labels available on day d:
    static     : alpha-quantile of validation positives (new-scheme view), frozen
    rolling    : alpha-quantile of ALL labelled positives so far (validation + stream labels after delay L)
    conformal  : finite-sample corrected alpha-quantile on a sliding window of recent labelled positives
NOTE: the conformal guarantee needs exchangeability. Cases in one scheme are dependent, time is ordered
and shift is constructed, so this module MEASURES how badly the nominal tolerance is violated; it never
asserts a guarantee.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .config import (
    BACKLOG_EXPIRY_DAYS,
    BOOTSTRAP_RESAMPLES,
    CONFORMAL_WINDOW_DAYS,
    LABEL_DELAY_DAYS,
    MIN_CALIBRATION_POSITIVES,
)


@dataclass(frozen=True)
class PolicyConfig:
    kind: str = "static"  # static | rolling | conformal
    alpha: float = 0.10
    label_delay: int = LABEL_DELAY_DAYS
    expiry: int = BACKLOG_EXPIRY_DAYS
    window: int = CONFORMAL_WINDOW_DAYS
    min_pos: int = MIN_CALIBRATION_POSITIVES
    label_regime: str = "oracle"  # oracle (all labels after delay) | review_only (selection bias)

    def to_dict(self) -> dict:
        return asdict(self)


def empirical_tau(scores: np.ndarray, alpha: float) -> float:
    return float(np.quantile(scores, alpha, method="lower")) if len(scores) else float("-inf")


def conformal_tau(scores: np.ndarray, alpha: float) -> float:
    """k-th smallest score with k = floor(alpha (n+1)); -inf (no auto-close) if k < 1."""
    n = len(scores)
    k = int(np.floor(alpha * (n + 1)))
    return float(np.sort(scores)[k - 1]) if k >= 1 else float("-inf")


def simulate(
    day: np.ndarray,
    score: np.ndarray,
    y: np.ndarray,
    *,
    r: float,
    policy: PolicyConfig,
    cal_scores: np.ndarray,
    family_mask: np.ndarray | None = None,
    cal_days: np.ndarray | None = None,
    return_zone: bool = False,
    cluster: np.ndarray | None = None,
) -> dict:
    """Run the day-by-day queue. Returns aggregate metrics + compact per-day series."""
    n = len(day)
    order = np.argsort(day, kind="stable")
    day, score, y = day[order], score[order], y[order]
    fm = family_mask[order] if family_mask is not None else np.zeros(n, dtype="int64")
    days = np.unique(day)
    starts = {d: (np.searchsorted(day, d, "left"), np.searchsorted(day, d, "right")) for d in days}

    static_tau = empirical_tau(cal_scores, policy.alpha)
    lab_scores: list[float] = list(cal_scores)  # labelled positive scores (initial calibration)
    lab_days: list[int] = [int(days[0]) - 10_000] * len(cal_scores) if cal_days is None else list(cal_days)
    known_pos = np.zeros(n, dtype=bool)  # review_only regime: revealed positives
    zone = np.zeros(n, dtype="int8")  # 1 review, 2 auto-close, 3 backlog(open), 4 expired
    pending: list[int] = []
    age: dict[int, int] = {}
    series: dict[str, list] = {
        "day": [],
        "n_new": [],
        "review": [],
        "auto_close": [],
        "backlog": [],
        "backlog_age": [],
        "tau": [],
        "expired": [],
    }
    pos_idx_by_day = {d: np.arange(*starts[d])[y[starts[d][0] : starts[d][1]] == 1] for d in days}
    revealed: set[int] = set()

    for d in days:
        a, b = starts[d]
        new = np.arange(a, b)
        # ---- tau_d from labels available on day d (labels of day e known once e <= d - delay)
        if policy.label_regime == "oracle":
            for e in days:
                if e > d - policy.label_delay:
                    break
                if e not in revealed:
                    revealed.add(e)
                    p = pos_idx_by_day[e]
                    lab_scores += list(score[p])
                    lab_days += [int(e)] * len(p)
        else:  # review_only: a positive is only labelled after it was REVIEWED (+ delay)
            for i in np.flatnonzero(known_pos):
                if day[i] <= d - policy.label_delay and (int(i) not in revealed):
                    revealed.add(int(i))
                    lab_scores.append(float(score[i]))
                    lab_days.append(int(day[i]))
        ls, ld = np.asarray(lab_scores), np.asarray(lab_days)
        if policy.kind == "none":  # REVIEW-only baseline: nothing is auto-closed
            tau = float("-inf")
        elif policy.kind == "static":
            tau = static_tau
        elif policy.kind == "rolling":
            tau = empirical_tau(ls, policy.alpha) if len(ls) >= policy.min_pos else static_tau
        elif policy.kind == "conformal":
            w = ls[ld > d - policy.window]
            tau = conformal_tau(w, policy.alpha) if len(w) >= policy.min_pos else float("-inf")
        else:
            raise ValueError(policy.kind)

        pool = np.array(pending + list(new), dtype="int64")
        K = int(np.ceil(r * len(new)))
        ranked = pool[np.lexsort((pool, -score[pool]))]
        rev, rest = ranked[:K], ranked[K:]
        zone[rev] = 1
        known_pos[rev[y[rev] == 1]] = True
        closed = rest[score[rest] <= tau]
        zone[closed] = 2
        left = rest[score[rest] > tau]
        pending, expired = [], 0
        for j in left:
            ci = int(j)
            age[ci] = age.get(ci, 0) + 1
            if age[ci] >= policy.expiry:
                zone[ci] = 4
                expired += 1
            else:
                zone[ci] = 3
                pending.append(ci)
        series["day"].append(int(d))
        series["n_new"].append(int(len(new)))
        series["review"].append(int(len(rev)))
        series["auto_close"].append(int(len(closed)))
        series["backlog"].append(int(len(pending)))
        series["backlog_age"].append(float(np.mean([age[i] for i in pending])) if pending else 0.0)
        series["tau"].append(None if not np.isfinite(tau) else float(tau))
        series["expired"].append(expired)

    P = int(y.sum())
    pos = y == 1
    ac_pos = int((pos & (zone == 2)).sum())
    res = {
        "policy": policy.to_dict(),
        "r": float(r),
        "n_cases": int(n),
        "n_positives": P,
        "review_recall": float((pos & (zone == 1)).sum() / max(P, 1)),
        "realised_miss_rate": ac_pos / max(P, 1),
        "expired_positive_rate": float((pos & (zone == 4)).sum() / max(P, 1)),
        "open_backlog_positive_rate": float((pos & (zone == 3)).sum() / max(P, 1)),
        "workload_removed": float((zone == 2).sum() / max(n, 1)),
        "review_share": float((zone == 1).sum() / max(n, 1)),
        "auto_closed_positives": ac_pos,
        "auto_closed_cases": int((zone == 2).sum()),
        "mean_backlog": float(np.mean(series["backlog"])),
        "max_backlog": int(np.max(series["backlog"])),
        "mean_backlog_age": float(np.mean(series["backlog_age"])),
        "series": series,
    }
    # weekly violation rate: share of 7-day windows with >=5 positives whose realised miss exceeds alpha
    wk = (day - day.min()) // 7
    v = tot = 0
    weekly = []
    for w in np.unique(wk):
        m = (wk == w) & pos
        if m.sum() >= 5:
            miss = float((zone[m] == 2).mean())
            weekly.append(miss)
            tot += 1
            v += miss > policy.alpha
    res["weekly_miss"] = weekly
    res["violation_rate"] = (v / tot) if tot else None
    res["n_weekly_windows"] = tot
    fam = {}
    for f in range(8):
        mf = pos & ((fm >> f) & 1 == 1)
        if mf.any():
            fam[str(f)] = {
                "n_pos": int(mf.sum()),
                "miss": float((zone[mf] == 2).mean()),
                "review_recall": float((zone[mf] == 1).mean()),
            }
    res["by_family"] = fam
    if cluster is not None and P > 0:
        cl = cluster[order][pos].copy()
        single = cl < 0
        cl[single] = -1 - np.arange(int(single.sum()))
        _, inv = np.unique(cl, return_inverse=True)
        zp = zone[pos]
        res["cluster_counts"] = {
            "n_pos": np.bincount(inv).tolist(),
            "n_closed": np.bincount(inv, weights=(zp == 2)).tolist(),
            "n_review": np.bincount(inv, weights=(zp == 1)).tolist(),
            "n_unreviewed_open_or_expired": np.bincount(inv, weights=np.isin(zp, (3, 4))).tolist(),
        }
    if return_zone:
        zone_in = np.zeros(n, dtype="int8")
        zone_in[order] = zone
        res["zone"] = zone_in  # 1 review, 2 auto-close, 3 backlog (open at end), 4 expired
    return res


def boot_rates(cc: dict, key: str, n_boot: int = BOOTSTRAP_RESAMPLES, seed: int = 3) -> list[float]:
    """95% scheme-cluster bootstrap interval of sum(cc[key]) / sum(n_pos)."""
    n_pos, k = np.asarray(cc["n_pos"], float), np.asarray(cc[key], float)
    idx = np.random.default_rng(seed).integers(0, len(n_pos), size=(n_boot, len(n_pos)))
    r = k[idx].sum(1) / np.maximum(n_pos[idx].sum(1), 1)
    return [float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))]
