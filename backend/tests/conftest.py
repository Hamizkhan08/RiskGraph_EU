"""Backend test fixtures: a handcrafted, schema-valid mini bundle (NOT research results)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from helpers_api import COLS, IDS, _detail, make_client  # noqa: E402


@pytest.fixture(scope="session")
def bundle_dir(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("bundle")
    d = root / "LI"
    (d / "model").mkdir(parents=True)
    rng = np.random.default_rng(0)
    X = rng.random((600, len(COLS)))
    y = (X[:, 0] + rng.normal(0, 0.3, 600) > 0.8).astype(int)
    lgb.LGBMClassifier(n_estimators=20, verbosity=-1, random_state=0).fit(X, y).booster_.save_model(
        str(d / "model" / "model_main.txt")
    )
    details = {cid: _detail(i, cid) for i, cid in enumerate(IDS)}
    alerts = [
        {k: v for k, v in x.items() if k not in ("explanation", "evidence", "features", "research")}
        for x in details.values()
    ]
    J = lambda n, o: (d / n).write_text(json.dumps(o))  # noqa: E731
    (root / "index.json").write_text(json.dumps({"datasets": [{"key": "LI", "label": "test"}], "default": "LI"}))
    J("summary.json", {"dataset": "LI", "primary": {"avg_review_per_day": 10.0}, "series": {"day": [1]}})
    J("alerts.json", alerts)
    J("case_details.json", details)
    J(
        "metrics.json",
        {"h1": {"calibration": {"M3": {"brier": 0.1, "bins": []}}, "pr_curve_main": []}, "h2": {}, "h3": {}},
    )
    J("monitoring.json", {"weekly": [], "calibration_windows": [], "feature_drift": []})
    J("data_quality.json", {"rows": 10})
    J("manifest.json", {"run_id": "test-run", "calibration": "platt", "dataset": {"name": "test"}})
    J(
        "model/feature_schema.json",
        {"model_features": COLS, "features": {c: {"group": "T", "definition": "x"} for c in COLS}},
    )
    J("model/calibration.json", {"type": "platt", "coef": 1.0, "intercept": -1.0})
    n = 20 * 200
    np.savez_compressed(
        d / "model" / "stream.npz",
        day=np.repeat(np.arange(20), 200).astype("int16"),
        score=rng.random(n).astype("float32"),
        y=(rng.random(n) < 0.02).astype("int8"),
        fm=np.zeros(n, "int16"),
        sch=rng.integers(0, 6, n).astype("int32"),
        cal_score=rng.random(60).astype("float32"),
        cal_day=np.full(60, -5, "int16"),
        p_train=np.float64(0.02),
    )
    return root


@pytest.fixture()
def client(bundle_dir, tmp_path) -> TestClient:
    return make_client(bundle_dir, tmp_path)
