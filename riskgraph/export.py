"""Turn a finished run (artifacts/runs/<run_id>) into the application bundle.

Everything shown in the app is produced here from recorded experiment outputs: the alert queue is
the REVIEW zone of the primary simulation, explanations are TreeSHAP of the actual model, evidence
is the actual transactions available at the decision timestamp. Nothing is typed by hand.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import config as C
from . import experiments as E
from .data.tide import load_tide
from .explain import REASON_LABELS, case_evidence, explain_rows
from .features.build import FEATURES
from .metrics import brier, daily_topk_mask, ece, pr_auc
from .models import PlattCalibrator
from .runs import write_json

LABELS = {
    "LI": "Low-illicit-ratio condition (locally generated Tide-format data)",
    "HI": "High-illicit-ratio condition (locally generated Tide-format data)",
}
DISCLOSURE = (
    "SYNTHETIC DATA — generated locally with the MIT-licensed Tide generator at reduced scale; "
    "not the published Zenodo release. Research prototype; not a detection system."
)


def _psi(ref: np.ndarray, cur: np.ndarray, bins: int = 10) -> float:
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    a = np.histogram(ref, edges)[0] / max(len(ref), 1) + 1e-4
    b = np.histogram(cur, edges)[0] / max(len(cur), 1) + 1e-4
    return float(np.sum((b - a) * np.log(b / a)))


def _priority(scores: np.ndarray) -> np.ndarray:
    """P1 = top 10 % of the queue by score, P2 = next 30 %, P3 = rest (documented rule)."""
    rank = scores.argsort()[::-1].argsort() / max(len(scores), 1)
    return np.where(rank < 0.10, "P1", np.where(rank < 0.40, "P2", "P3"))


def export_dataset(run_dir: Path, data_dir: Path, key: str, out: Path, sample_per_week: int = 20) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text())
    h1, h2, h3 = (json.loads((run_dir / f"{n}.json").read_text()) for n in ("h1", "h2", "h3"))
    dq = json.loads((run_dir / "data_quality.json").read_text())
    seeds = manifest["seeds"]
    td = load_tide(data_dir)
    prep = E.prepare(td, cache=C.DATA_DIR / "interim")
    ct, sp = prep.ct, prep.sp
    z = np.load(run_dir / "scores_h1.npz")
    scores = {(k.split("__")[0], int(k.split("__")[1])): z[k] for k in z.files if k != "rows"}
    s_main = scores[(E.MAIN, seeds[0])]
    v = E.Views(prep)
    cols = E.cols_of(E.MODELS[E.MAIN])
    booster = lgb.Booster(model_file=str(run_dir / "model_main.txt"))
    shim = SimpleNamespace(kind="lgbm", cols=cols, est=SimpleNamespace(booster_=booster))
    cal = PlattCalibrator().fit(s_main[v.val_cal], v.y[v.val_cal])
    p_cal = cal.transform(s_main)

    # ---- primary simulation -> queue ------------------------------------------------------------
    prim = E.primary_simulation(prep, scores, seeds[0])
    zone = prim.pop("zone")
    pos_in_rows = np.flatnonzero(v.test_strict)  # stream position -> position in rows
    stream_day = v.day[pos_in_rows]
    review_stream = np.flatnonzero(zone == 1)
    rng = np.random.default_rng(5)
    chosen: list[int] = []
    wk = (stream_day[review_stream] - stream_day.min()) // 7
    for w in np.unique(wk):
        idx = review_stream[wk == w]
        order = idx[np.argsort(-s_main[pos_in_rows[idx]])]
        top, rest = list(order[: sample_per_week // 2]), list(order[sample_per_week // 2 :])
        rng.shuffle(rest)
        chosen += top + rest[: sample_per_week - len(top)]
    chosen = sorted(set(chosen), key=lambda i: (stream_day[i], -s_main[pos_in_rows[i]]))
    g_rows = prep.rows[pos_in_rows[chosen]]  # global case indices
    Xc = ct.X.iloc[g_rows]
    expl = explain_rows(shim, Xc, top=6)
    pri = _priority(s_main[pos_in_rows[chosen]])
    alerts, details = [], {}
    for j, gi in enumerate(g_rows):
        a, d = int(ct.acct[gi]), int(ct.day[gi])
        date = (td.start_date + pd.Timedelta(days=d)).date()
        cid = f"RG-{key}-{str(td.accounts[a]).split('_')[1]}-{date:%Y%m%d}"
        x = Xc.iloc[j]
        sc = float(s_main[pos_in_rows[chosen[j]]])
        rc = expl[j]["reasons"][0]
        net = {
            "degree_7d": float(x.g_deg_und_7d),
            "reach2_7d": float(x.g_reach2_7d),
            "hub_neighbour_share": float(x.g_nbr_hub_share_7d),
            "cycles": {"c2": float(x.m_cycle2_7d), "c3": float(x.m_cycle3_7d), "c4": float(x.m_cycle4_7d)},
            "fanin_burst_3d": float(x.m_fanin_burst_3d),
            "fanout_burst_3d": float(x.m_fanout_burst_3d),
        }
        amounts = {
            "out_1d": float(x.t_amt_out_1d),
            "in_1d": float(x.t_amt_in_1d),
            "out_7d": float(x.t_amt_out_7d),
            "in_7d": float(x.t_amt_in_7d),
            "n_tx_1d": float(x.t_n_out_1d + x.t_n_in_1d),
            "note": "nominal units; source data has no FX conversion",
        }
        fam = int(ct.family_mask[gi]).bit_length() - 1
        light = {
            "id": cid,
            "dataset": key,
            "account": str(td.accounts[a]),
            "date": str(date),
            "decision_timestamp": str(td.start_date + pd.Timedelta(days=d + 1)),
            "score": sc,
            "p_cal": float(p_cal[pos_in_rows[chosen[j]]]),
            "priority": str(pri[j]),
            "status": "open",
            "key_reason": rc["label"],
            "key_reason_code": rc["code"],
            "network": net,
            "amounts": amounts,
        }
        alerts.append(light)
        details[cid] = {
            **light,
            "explanation": expl[j],
            "evidence": case_evidence(td, a, d),
            "features": {c: float(x[c]) for c in cols},
            "research": {
                "ground_truth_positive": int(ct.y[gi]),
                "family": td.families[fam] if ct.y[gi] and fam >= 0 else None,
                "scheme_id": (
                    td.schemes.set_index("scheme_idx").loc[int(ct.scheme_first[gi]), "scheme_id"]
                    if ct.y[gi] and ct.scheme_first[gi] >= 0
                    else None
                ),
                "note": "synthetic ground truth — research view only, never a model input",
            },
        }

    # ---- dashboard summary ------------------------------------------------------------------------
    ser = prim["series"]
    cc = prim.get("cluster_counts")
    summary = {
        "dataset": key,
        "label": LABELS[key],
        "disclosure": DISCLOSURE,
        "run_id": manifest["run_id"],
        "generated_at": manifest["timestamp_utc"],
        "split": manifest["split"],
        "counts": h1["counts"],
        "primary": {
            "policy": prim["policy"],
            "capacity_multiplier": C.PRIMARY_CAPACITY_MULTIPLIER,
            "avg_review_per_day": float(np.mean(ser["review"])),
            "n_review_total": int(np.sum(ser["review"])),
            "n_cases": prim["n_cases"],
            "n_positives": prim["n_positives"],
            "review_recall": prim["review_recall"],
            "auto_closed_cases": prim["auto_closed_cases"],
            "realised_miss_rate": prim["realised_miss_rate"],
            "expired_positive_rate": prim["expired_positive_rate"],
            "open_backlog_positive_rate": prim["open_backlog_positive_rate"],
            "mean_backlog": prim["mean_backlog"],
            "max_backlog": prim["max_backlog"],
            "mean_backlog_age": prim["mean_backlog_age"],
            "violation_rate": prim["violation_rate"],
            "miss_ci95": E.boot_rates(cc, "n_closed") if cc else None,
            "n_clusters": len(cc["n_pos"]) if cc else None,
        },
        "series": {
            "day": ser["day"],
            "date": [str((td.start_date + pd.Timedelta(days=int(d))).date()) for d in ser["day"]],
            "n_new": ser["n_new"],
            "review": ser["review"],
            "auto_close": ser["auto_close"],
            "backlog": ser["backlog"],
            "backlog_age": ser["backlog_age"],
            "tau": ser["tau"],
            "expired": ser["expired"],
        },
        "queue_sample": {
            "n": len(alerts),
            "of_total_review": int(len(review_stream)),
            "rule": f"up to {sample_per_week} per week: top {sample_per_week // 2} by score + random remainder",
        },
    }

    # ---- metrics bundle -----------------------------------------------------------------------------
    imp = pd.Series(booster.feature_importance("gain"), index=cols).sort_values(ascending=False)
    grid = [
        {
            "policy": c["policy"]["kind"],
            "alpha": c["policy"]["alpha"],
            "m": c["m"],
            "n_pos": c["n_positives"],
            "realised_miss_rate": c["realised_miss_rate"],
            "miss_ci95": c.get("miss_ci95"),
            "review_recall": c["review_recall"],
            "unreviewed_rate": 1 - c["review_recall"],
            "expired_positive_rate": c["expired_positive_rate"],
            "workload_removed": c["workload_removed"],
            "auto_closed_cases": c["auto_closed_cases"],
            "mean_backlog": c["mean_backlog"],
            "max_backlog": c["max_backlog"],
            "violation_rate": c["violation_rate"],
            "n_weekly_windows": c["n_weekly_windows"],
        }
        for c in h3["same_regime"]
    ]
    base = {
        m: {k: b[k] for k in ("review_recall", "expired_positive_rate", "mean_backlog", "max_backlog")}
        for m, b in h3["baseline_no_autoclose"].items()
    }
    metrics = {
        "dataset": key,
        "label": LABELS[key],
        "disclosure": DISCLOSURE,
        "run_id": manifest["run_id"],
        "h1": h1,
        "h2": h2,
        "h3": {
            "stream": h3["stream"],
            "same_regime": grid,
            "baseline_no_autoclose": base,
            "heldout": [
                {
                    k: c.get(k)
                    for k in (
                        "heldout_family_name",
                        "policy",
                        "realised_miss_rate",
                        "miss_ci95",
                        "workload_removed",
                        "violation_rate",
                        "heldout_family_stats",
                        "n_clusters",
                    )
                }
                for c in h3["heldout"]
            ],
            "review_only_labels": [
                {k: c.get(k) for k in ("policy", "realised_miss_rate", "miss_ci95", "workload_removed")}
                for c in h3["review_only_labels"]
            ],
        },
        "feature_importance_gain": [
            {"feature": str(f), "gain": float(g), "group": FEATURES[str(f)][0], "definition": FEATURES[str(f)][1]}
            for f, g in imp.head(15).items()
        ],
        "families": manifest["families"],
        "models": {k: {"label": m["label"], "features": len(m["features"])} for k, m in manifest["models"].items()},
    }

    # ---- monitoring: backtest replay over validation + test (observed on synthetic data) ------------
    d_all = v.day
    masks = v.val_cal | v.test_strict
    r1 = prep.r_grid[1.0]
    weekly = []
    for w0 in range(sp.val[0], sp.n_days, 7):
        m = masks & (d_all >= w0) & (d_all < w0 + 7)
        if m.sum() < 100:
            continue
        rv = daily_topk_mask(d_all[m], s_main[m], r1)
        yy = v.y[m]
        weekly.append(
            {
                "week_start": str((td.start_date + pd.Timedelta(days=w0)).date()),
                "block": "validation" if w0 < sp.val[1] else "test",
                "n_cases": int(m.sum()),
                "n_pos": int(yy.sum()),
                "n_review_at_m1": int(rv.sum()),
                "recall_at_m1": float(rv[yy == 1].mean()) if yy.sum() else None,
                "mean_p_cal": float(p_cal[m].mean()),
                "p50": float(np.quantile(p_cal[m], 0.5)),
                "p90": float(np.quantile(p_cal[m], 0.9)),
                "p99": float(np.quantile(p_cal[m], 0.99)),
                "pr_auc": pr_auc(yy, s_main[m]) if yy.sum() >= 5 else None,
            }
        )
    tr_idx = np.flatnonzero((ct.day >= sp.train[0]) & (ct.day < sp.train[1]))
    ref = ct.X.iloc[rng.choice(tr_idx, min(150_000, len(tr_idx)), replace=False)]
    top_feats = list(imp.head(10).index)
    drift = []
    for w0 in range(sp.val[0], sp.n_days, 28):
        m = (d_all >= w0) & (d_all < w0 + 28)
        if m.sum() < 1000:
            continue
        cur = ct.X.iloc[prep.rows[m]]
        drift.append(
            {
                "window_start": str((td.start_date + pd.Timedelta(days=w0)).date()),
                "psi": {f: _psi(ref[f].to_numpy(), cur[f].to_numpy()) for f in top_feats},
            }
        )
    calw = []
    for w0 in range(sp.val[0], sp.n_days, 28):
        m = masks & (d_all >= w0) & (d_all < w0 + 28)
        if m.sum() < 1000 or v.y[m].sum() < 5:
            continue
        calw.append(
            {
                "window_start": str((td.start_date + pd.Timedelta(days=w0)).date()),
                "n_pos": int(v.y[m].sum()),
                "brier": brier(v.y[m], p_cal[m]),
                "ece": ece(v.y[m], p_cal[m]),
                "mean_pred": float(p_cal[m].mean()),
                "obs_rate": float(v.y[m].mean()),
            }
        )
    monitoring = {
        "dataset": key,
        "mode": "BACKTEST REPLAY — observed on synthetic data; not live monitoring",
        "disclosure": DISCLOSURE,
        "weekly": weekly,
        "feature_drift": drift,
        "calibration_windows": calw,
        "top_features": top_feats,
        "psi_note": "PSI vs training block; rule of thumb 0.1 = moderate, 0.25 = major",
        "score_definition": "Platt-calibrated probability of the main model (validation, new-scheme view)",
    }

    # ---- write ------------------------------------------------------------------------------------------
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "summary.json", summary)
    write_json(out / "alerts.json", alerts)
    write_json(out / "case_details.json", details)
    write_json(out / "metrics.json", metrics)
    write_json(out / "monitoring.json", monitoring)
    write_json(out / "data_quality.json", dq)
    write_json(out / "manifest.json", manifest)
    mdir = out / "model"
    mdir.mkdir(exist_ok=True)
    shutil.copy(run_dir / "model_main.txt", mdir / "model_main.txt")
    write_json(
        mdir / "feature_schema.json",
        {
            "model_features": cols,
            "features": {k: {"group": g, "definition": d} for k, (g, d) in FEATURES.items()},
            "reason_labels": REASON_LABELS,
        },
    )
    write_json(
        mdir / "calibration.json",
        {
            "type": "platt",
            "coef": float(cal.lr.coef_[0][0]),
            "intercept": float(cal.lr.intercept_[0]),
            "input": "logit(clip(score,1e-6,1-1e-6))",
        },
    )
    m = v.test_strict
    np.savez_compressed(
        mdir / "stream.npz",
        day=v.day[m].astype("int16"),
        score=s_main[m].astype("float32"),
        y=v.y[m].astype("int8"),
        fm=v.fm[m].astype("int16"),
        sch=v.sch[m].astype("int32"),
        cal_score=s_main[v.val_cal & (v.y == 1)].astype("float32"),
        cal_day=v.day[v.val_cal & (v.y == 1)].astype("int16"),
        p_train=np.float64(prep.p_train),
    )
    return {"key": key, "alerts": len(alerts), "review_total": int(len(review_stream))}
