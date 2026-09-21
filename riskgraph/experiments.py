"""Experiment stages H1 / H2 / H3. Every reported number is produced here and stored with the
run manifest; nothing is typed by hand into docs or UI (scripts/render_results.py renders docs)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from . import config as C
from .data.schema import TxData
from .decision import PolicyConfig, boot_rates, simulate
from .features.build import CaseTable, build_cases, feature_names, load_cases, save_cases
from .metrics import (
    brier,
    calibration_bins,
    cluster_bootstrap_recall,
    daily_topk_mask,
    ece,
    pr_auc,
    pr_curve_points,
    topk_summary,
)
from .models import PlattCalibrator, ScoreModel
from .split import Split, block_mask, eval_mask, make_split, window_mask

log = logging.getLogger("riskgraph")
NO_TYPE = [
    "t_n_transfer_out_1d",
    "t_n_transfer_in_1d",
    "t_n_deposit_1d",
    "t_n_withdrawal_1d",
    "t_n_payment_1d",
    "t_transfer_share_7d",
]
MODELS: dict[str, dict] = {
    "M1_logreg_TB": dict(kind="logreg", groups=("T", "B"), label="Logistic regression (T+B)"),
    "M2_lgbm_TB": dict(
        kind="lgbm", groups=("T", "B"), label="Gradient boosting (T+B) — transaction/behaviour baseline"
    ),
    "M3_lgbm_TBG": dict(kind="lgbm", groups=("T", "B", "G"), label="Graph-enhanced gradient boosting (T+B+G)"),
    "M4_lgbm_TBGM": dict(kind="lgbm", groups=("T", "B", "G", "M"), label="Typology/motif-aware boosting (T+B+G+M)"),
    "A1_lgbm_T": dict(kind="lgbm", groups=("T",), label="Ablation: own activity only (T)"),
    "A2_lgbm_TBG_notype": dict(
        kind="lgbm", groups=("T", "B", "G"), drop=NO_TYPE, label="Ablation: T+B+G without transaction-type features"
    ),
}
MAIN = "M3_lgbm_TBG"


def cols_of(spec: dict) -> list[str]:
    return [c for c in feature_names(spec["groups"]) if c not in spec.get("drop", [])]


@dataclass
class Prepared:
    td: TxData
    ct: CaseTable
    sp: Split
    p_train: float
    rows: np.ndarray  # case indices with day >= validation start (scored rows)
    h2_start: int  # start of the post-training window used for H2

    @property
    def r_grid(self) -> dict[float, float]:
        return {m: m * self.p_train for m in C.CAPACITY_MULTIPLIERS}


def prepare(td: TxData, cache: Path | None = None) -> Prepared:
    ct = None
    key = f"{td.name}-{C.FEATURE_VERSION}-{td.meta.get('files_sha256', {}).get('generated_transactions.csv', 'x')[:12]}"
    if cache is not None and (cache / f"{key}.npz").exists():
        ct = load_cases(cache / f"{key}.npz")
    if ct is None:
        t = time.time()
        ct = build_cases(td)
        log.info("features built in %.0fs (%d cases, %d positives)", time.time() - t, len(ct.y), int(ct.y.sum()))
        if cache is not None:
            cache.mkdir(parents=True, exist_ok=True)
            save_cases(ct, cache / f"{key}.npz")
    sp = make_split(td.n_days)
    tr = block_mask(ct, sp, "train")
    rows = np.flatnonzero(ct.day >= sp.val[0])
    return Prepared(td=td, ct=ct, sp=sp, p_train=float(ct.y[tr].mean()), rows=rows, h2_start=sp.train[1] + C.PURGE_DAYS)


def _fit(prep: Prepared, name: str, seed: int, train_mask: np.ndarray) -> tuple[ScoreModel, np.ndarray]:
    spec = MODELS[name]
    m = ScoreModel(spec["kind"], cols_of(spec), seed)
    idx = np.flatnonzero(train_mask)
    m.fit(prep.ct.X.iloc[idx], prep.ct.y[idx])
    return m, m.score(prep.ct.X.iloc[prep.rows]).astype("float32")


class Views:
    """Row-aligned masks/arrays over prep.rows."""

    def __init__(self, prep: Prepared):
        ct, sp, rows = prep.ct, prep.sp, prep.rows
        self.y, self.day = ct.y[rows], ct.day[rows]
        self.sch, self.fm = ct.scheme_first[rows], ct.family_mask[rows]
        self.val_cal = eval_mask(ct, sp, "val", "strict")[rows]
        self.test_strict = eval_mask(ct, sp, "test", "strict")[rows]
        self.test_all = eval_mask(ct, sp, "test", "all")[rows]
        self.win_strict = window_mask(ct, prep.h2_start, None, "strict")[rows]


def _block_metrics(prep: Prepared, v: Views, score: np.ndarray, mask: np.ndarray) -> dict:
    y, day, s = v.y[mask], v.day[mask], score[mask]
    return {
        "n_cases": int(mask.sum()),
        "n_pos": int(y.sum()),
        "pr_auc": pr_auc(y, s),
        "topk": {str(m): topk_summary(day, s, y, r) for m, r in prep.r_grid.items()},
    }


def _agg(vals: list[float]) -> dict:
    a = np.asarray(vals, dtype=float)
    return {"mean": float(np.nanmean(a)), "sd": float(np.nanstd(a)), "values": [float(x) for x in a]}


# ----------------------------------------------------------------------------------------------
def stage_h1(prep: Prepared, seeds=C.SEEDS) -> tuple[dict, dict, dict]:
    """Feature-group ablation. Returns (results, scores{(name,seed)}, models{(name,seed)})."""
    v = Views(prep)
    train = block_mask(prep.ct, prep.sp, "train")
    scores, models = {}, {}
    for name in MODELS:
        for seed in seeds:
            t = time.time()
            models[(name, seed)], scores[(name, seed)] = _fit(prep, name, seed, train)
            log.info("H1 fit %s seed=%d in %.0fs", name, seed, time.time() - t)
    res: dict = {"models": {}, "contrasts": [], "calibration": {}}
    for name in MODELS:
        per_view = {}
        for view, mask in (("strict", v.test_strict), ("all", v.test_all)):
            runs = [_block_metrics(prep, v, scores[(name, s)], mask) for s in seeds]
            per_view[view] = {
                "n_cases": runs[0]["n_cases"],
                "n_pos": runs[0]["n_pos"],
                "pr_auc": _agg([r["pr_auc"] for r in runs]),
                "topk": {
                    m: {k: _agg([r["topk"][m][k] for r in runs]) for k in ("recall", "precision", "lift")}
                    | {"n_pos": runs[0]["topk"][m]["n_pos"], "avg_k_per_day": runs[0]["topk"][m]["avg_k_per_day"]}
                    for m in runs[0]["topk"]
                },
            }
        res["models"][name] = {
            "label": MODELS[name]["label"],
            "n_features": len(cols_of(MODELS[name])),
            "test": per_view,
        }
    # paired scheme-cluster bootstrap on seed[0]
    s0 = seeds[0]
    pairs = [
        ("M3_lgbm_TBG", "M2_lgbm_TB"),
        ("M4_lgbm_TBGM", "M3_lgbm_TBG"),
        ("M3_lgbm_TBG", "A2_lgbm_TBG_notype"),
        ("M2_lgbm_TB", "M1_logreg_TB"),
        ("M2_lgbm_TB", "A1_lgbm_T"),
    ]
    mk = v.test_strict
    for a, b in pairs:
        for m_, r in prep.r_grid.items():
            ra = daily_topk_mask(v.day[mk], scores[(a, s0)][mk], r)
            rb = daily_topk_mask(v.day[mk], scores[(b, s0)][mk], r)
            st = cluster_bootstrap_recall(v.sch[mk], v.y[mk], ra, rb, C.BOOTSTRAP_RESAMPLES, seed=1)
            res["contrasts"].append(
                {
                    "a": a,
                    "b": b,
                    "m": m_,
                    "primary": (a, b, m_) == (MAIN, "M2_lgbm_TB", C.PRIMARY_CAPACITY_MULTIPLIER),
                    **st,
                }
            )
    # calibration of every model on validation (strict), evaluated on test (strict)
    for name in MODELS:
        cal = PlattCalibrator().fit(scores[(name, s0)][v.val_cal], v.y[v.val_cal])
        p = cal.transform(scores[(name, s0)][mk])
        res["calibration"][name] = {
            "brier": brier(v.y[mk], p),
            "ece": ece(v.y[mk], p),
            "bins": calibration_bins(v.y[mk], p),
            "n_val_pos": int(v.y[v.val_cal].sum()),
            "prevalence_test": float(v.y[mk].mean()),
            "brier_baseline_prevalence": brier(v.y[mk], np.full(mk.sum(), v.y[v.val_cal].mean())),
        }
    res["pr_curve_main"] = pr_curve_points(v.y[mk], scores[(MAIN, s0)][mk])
    res["counts"] = {
        "train_cases": int(block_mask(prep.ct, prep.sp, "train").sum()),
        "train_pos": int(prep.ct.y[train].sum()),
        "val_cal_cases": int(v.val_cal.sum()),
        "val_cal_pos": int(v.y[v.val_cal].sum()),
        "test_strict_cases": int(v.test_strict.sum()),
        "test_strict_pos": int(v.y[v.test_strict].sum()),
        "test_strict_schemes": int(len(np.unique(v.sch[v.test_strict & (v.y == 1)]))),
        "test_all_pos": int(v.y[v.test_all].sum()),
        "p_train": prep.p_train,
    }
    return res, scores, models


def stage_h2(prep: Prepared, h1_scores: dict, seeds=C.SEEDS) -> tuple[dict, dict]:
    """Leave-one-family-out. Returns (results, held_out_scores{(fam,name,seed)})."""
    v = Views(prep)
    ct = prep.ct
    train = block_mask(ct, prep.sp, "train")
    fams = [f for f in range(len(prep.td.families)) if ((ct.family_mask >> f) & 1).any()]
    held: dict = {}
    out: dict[str, Any] = {"families": {}, "window_start_day": prep.h2_start}
    specs = ("M3_lgbm_TBG", "M4_lgbm_TBGM")
    for f in fams:
        bit = 1 << f
        tr_f = train & ((ct.family_mask & bit) == 0)
        for name in specs:
            for seed in seeds:
                _, held[(f, name, seed)] = _fit(prep, name, seed, tr_f)
        restrict = v.win_strict & ((v.y == 0) | (v.fm == bit))
        d, y, sch = v.day[restrict], v.y[restrict], v.sch[restrict]
        rec: dict[str, Any] = {
            "family": prep.td.families[f],
            "n_pos_cases": int(y.sum()),
            "n_schemes": int(len(np.unique(sch[y == 1]))),
            "n_train_cases_removed": int((train & ~tr_f).sum()),
            "by_m": {},
        }
        for m_, r in prep.r_grid.items():
            per: dict[str, Any] = {}
            for name in specs:
                seen = [topk_summary(d, h1_scores[(name, s)][restrict], y, r)["recall"] for s in seeds]
                hold = [topk_summary(d, held[(f, name, s)][restrict], y, r)["recall"] for s in seeds]
                per[name] = {
                    "recall_seen": _agg(seen),
                    "recall_heldout": _agg(hold),
                    "rel_loss": _agg([(a - b) / a if a > 0 else float("nan") for a, b in zip(seen, hold)]),
                }
            # paired scheme-cluster bootstrap of relative loss, seed[0]
            s0 = seeds[0]
            cl = np.where(y == 1, sch, -1)
            ids, inv = np.unique(cl[y == 1], return_inverse=True)
            nums = {}
            for name in specs:
                for tag, sc in (("seen", h1_scores[(name, s0)][restrict]), ("held", held[(f, name, s0)][restrict])):
                    rv = daily_topk_mask(d, sc, r)
                    nums[(name, tag)] = np.bincount(inv, weights=rv[y == 1].astype(float), minlength=len(ids))
            rng = np.random.default_rng(2)
            idx = rng.integers(0, max(len(ids), 1), size=(C.BOOTSTRAP_RESAMPLES, max(len(ids), 1)))

            def loss(name):
                s_, h_ = nums[(name, "seen")][idx].sum(1), nums[(name, "held")][idx].sum(1)
                return np.where(s_ > 0, 1 - h_ / np.maximum(s_, 1e-9), np.nan)

            l3, l4 = loss("M3_lgbm_TBG"), loss("M4_lgbm_TBGM")
            per["diff_loss_M4_minus_M3"] = {
                "ci95": [float(np.nanpercentile(l4 - l3, 2.5)), float(np.nanpercentile(l4 - l3, 97.5))],
                "point": float(
                    np.nanmean(per["M4_lgbm_TBGM"]["rel_loss"]["values"])
                    - np.nanmean(per["M3_lgbm_TBG"]["rel_loss"]["values"])
                ),
                "loss_M3_ci95": [float(np.nanpercentile(l3, 2.5)), float(np.nanpercentile(l3, 97.5))],
                "loss_M4_ci95": [float(np.nanpercentile(l4, 2.5)), float(np.nanpercentile(l4, 97.5))],
            }
            rec["by_m"][str(m_)] = per
        out["families"][str(f)] = rec
    return out, held


def stage_h3(prep: Prepared, h1_scores: dict, held: dict, seeds=C.SEEDS) -> dict:
    """Auto-close policies: same-regime and held-out-family shift."""
    v = Views(prep)
    s0 = seeds[0]
    mk = v.test_strict
    day, y, fm = v.day[mk], v.y[mk], v.fm[mk]
    out: dict = {
        "stream": {"n_cases": int(mk.sum()), "n_pos": int(y.sum()), "days": [int(day.min()), int(day.max())]},
        "same_regime": [],
        "heldout": [],
        "review_only_labels": [],
        "baseline_no_autoclose": {},
    }
    pol = lambda kind, a, reg="oracle": PolicyConfig(kind=kind, alpha=a, label_regime=reg)  # noqa: E731

    def run(score_all, cal_mask, m_, kind, a, reg="oracle"):
        cal_s, cal_d = score_all[cal_mask & (v.y == 1)], v.day[cal_mask & (v.y == 1)]
        res = simulate(
            day,
            score_all[mk],
            y,
            r=m_ * prep.p_train,
            policy=pol(kind, a, reg),
            cal_scores=cal_s,
            cal_days=cal_d,
            family_mask=fm,
            cluster=v.sch[mk],
        )
        if "cluster_counts" in res:
            res["miss_ci95"] = boot_rates(res["cluster_counts"], "n_closed")
            res["n_clusters"] = len(res["cluster_counts"]["n_pos"])
            res["unreviewed_rate"] = float(1 - res["review_recall"])
        res.pop(
            "series", None
        ) if kind != "static" or a != C.PRIMARY_ALPHA or m_ != C.PRIMARY_CAPACITY_MULTIPLIER else None
        res["n_cal_pos"] = int(len(cal_s))
        return res

    for m_ in C.CAPACITY_MULTIPLIERS:
        out["baseline_no_autoclose"][str(m_)] = {
            k: v_
            for k, v_ in run(h1_scores[(MAIN, s0)], v.val_cal, m_, "none", 0.0).items()
            if k not in ("series", "weekly_miss")
        }
        for kind in ("static", "rolling", "conformal"):
            for a in C.ALPHA_GRID:
                r_ = run(h1_scores[(MAIN, s0)], v.val_cal, m_, kind, a)
                r_["m"], r_["scenario"] = m_, "same_regime"
                out["same_regime"].append(r_)
    for f in sorted({k[0] for k in held}):
        bit = 1 << f
        cal_mask = v.val_cal & ((v.fm & bit) == 0)
        for kind in ("static", "rolling", "conformal"):
            for a in C.ALPHA_GRID:
                r_ = run(held[(f, MAIN, s0)], cal_mask, C.PRIMARY_CAPACITY_MULTIPLIER, kind, a)
                r_["heldout_family"], r_["heldout_family_name"] = f, prep.td.families[f]
                r_["scenario"] = "heldout_family"
                r_["heldout_family_stats"] = r_["by_family"].get(str(f))
                out["heldout"].append(r_)
    for kind in ("rolling", "conformal"):
        r_ = run(h1_scores[(MAIN, s0)], v.val_cal, C.PRIMARY_CAPACITY_MULTIPLIER, kind, C.PRIMARY_ALPHA, "review_only")
        r_["scenario"] = "same_regime_review_only_labels"
        out["review_only_labels"].append(r_)
    return out


def primary_simulation(prep: Prepared, h1_scores: dict, seed: int) -> dict:
    """Primary policy (static, alpha=0.10, m=1) with per-case zones -> the analyst queue."""
    v = Views(prep)
    mk = v.test_strict
    cal = v.val_cal & (v.y == 1)
    res = simulate(
        v.day[mk],
        h1_scores[(MAIN, seed)][mk],
        v.y[mk],
        r=C.PRIMARY_CAPACITY_MULTIPLIER * prep.p_train,
        policy=PolicyConfig("static", C.PRIMARY_ALPHA),
        cal_scores=h1_scores[(MAIN, seed)][cal & True],
        cal_days=v.day[cal],
        family_mask=v.fm[mk],
        return_zone=True,
        cluster=v.sch[mk],
    )
    return res
