"""Run manifests: every result is traceable to dataset, split, features, models, seeds, parameters."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd

from . import config as C
from .experiments import MODELS, Prepared, cols_of


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def make_manifest(prep: Prepared, seeds: tuple[int, ...]) -> dict:
    td, sp = prep.td, prep.sp
    d0 = td.start_date

    def rng(b: tuple[int, int]) -> dict:
        return {
            "days": [int(b[0]), int(b[1])],
            "dates": [
                str((d0 + pd.Timedelta(days=int(b[0]))).date()),
                str((d0 + pd.Timedelta(days=int(b[1]) - 1)).date()),
            ],
        }

    return {
        "run_id": f"{td.name}-{C.FEATURE_VERSION}-r1",
        "timestamp_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "pipeline_version": C.PIPELINE_VERSION,
        "feature_version": C.FEATURE_VERSION,
        "dataset": {
            k: td.meta.get(k)
            for k in (
                "name",
                "adapter",
                "generator",
                "generator_commit",
                "seed",
                "config",
                "period_days",
                "start_date",
                "source_note",
                "files_sha256",
                "excluded_columns",
            )
        },
        "unit_of_analysis": "account-day; decision timestamp = end of day d",
        "split": {
            "burn_in": rng((0, sp.burn_in)),
            "train": rng(sp.train),
            "validation": rng(sp.val),
            "purge": rng(sp.purge),
            "test": rng(sp.test),
            "h2_window_start_day": prep.h2_start,
        },
        "seeds": list(seeds),
        "lgbm_params": C.LGBM_PARAMS,
        "neg_train_fraction": C.NEG_TRAIN_FRACTION,
        "capacity": {
            "multipliers": list(C.CAPACITY_MULTIPLIERS),
            "primary": C.PRIMARY_CAPACITY_MULTIPLIER,
            "train_prevalence_cases": prep.p_train,
            "rule": "K_d = ceil(m * p_train * new_cases_d)",
        },
        "policy": {
            "alpha_grid": list(C.ALPHA_GRID),
            "primary_alpha": C.PRIMARY_ALPHA,
            "label_delay_days": C.LABEL_DELAY_DAYS,
            "backlog_expiry_days": C.BACKLOG_EXPIRY_DAYS,
            "conformal_window_days": C.CONFORMAL_WINDOW_DAYS,
            "min_calibration_positives": C.MIN_CALIBRATION_POSITIVES,
        },
        "calibration": "Platt (sigmoid) on validation, strict view (new schemes only)",
        "evaluation_views": {
            "strict": "drops positive cases whose schemes all started before the block (primary)",
            "all": "keeps them (sensitivity)",
        },
        "models": {k: {"kind": v["kind"], "features": cols_of(v), "label": v["label"]} for k, v in MODELS.items()},
        "families": td.families,
        "bootstrap": {"resamples": C.BOOTSTRAP_RESAMPLES, "unit": "scheme cluster"},
    }


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
