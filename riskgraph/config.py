"""Central configuration: paths, versions, pre-declared experiment constants.

Decision timestamp (documented, enforced by tests): a case is (account, day d). Its decision
timestamp is the END of day d, i.e. 00:00 of day d+1. Features may use only transactions with
timestamp strictly before that instant. Labels are never used as features.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("RISKGRAPH_DATA_DIR", ROOT / "data"))
ARTIFACTS_DIR = Path(os.environ.get("RISKGRAPH_ARTIFACTS_DIR", ROOT / "artifacts"))

PIPELINE_VERSION = "1.0.0"
FEATURE_VERSION = "fv1"

# ---- Pre-declared experiment constants (fixed before any model was fitted) -----------------
SEEDS = (11, 23, 37)
BURN_IN_DAYS = 30  # feature history only (30-day windows need it); not scored
TRAIN_END_FRACTION = 0.575  # of the in-period days
VAL_END_FRACTION = 0.74
PURGE_DAYS = 14
CAPACITY_MULTIPLIERS = (0.5, 1.0, 2.0, 5.0)  # m in r = m * prevalence_train
PRIMARY_CAPACITY_MULTIPLIER = 1.0
ALPHA_GRID = (0.05, 0.10, 0.20)  # nominal auto-close miss tolerances
PRIMARY_ALPHA = 0.10
LABEL_DELAY_DAYS = 3  # L: labels available after L days
BACKLOG_EXPIRY_DAYS = 3  # M
CONFORMAL_WINDOW_DAYS = 60
MIN_CALIBRATION_POSITIVES = 20
NEG_TRAIN_FRACTION = 0.04  # negatives kept for TRAINING only
BOOTSTRAP_RESAMPLES = 500

LGBM_PARAMS: dict[str, Any] = dict(  # fixed a priori; no tuning
    n_estimators=300,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=20,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    verbosity=-1,
    n_jobs=1,
)
