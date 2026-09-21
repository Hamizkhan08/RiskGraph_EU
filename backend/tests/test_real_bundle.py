"""Schema/consistency validation of the SHIPPED bundle (skipped if it has not been built)."""

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "demo"
pytestmark = pytest.mark.skipif(not (ROOT / "index.json").exists(), reason="artifacts/demo not built")


def datasets():
    return [d["key"] for d in json.loads((ROOT / "index.json").read_text())["datasets"]]


@pytest.mark.parametrize("key", datasets() if (ROOT / "index.json").exists() else [])
def test_bundle_is_internally_consistent(key):
    d = ROOT / key
    alerts = json.loads((d / "alerts.json").read_text())
    details = json.loads((d / "case_details.json").read_text())
    schema = json.loads((d / "model" / "feature_schema.json").read_text())
    summary = json.loads((d / "summary.json").read_text())
    assert len(alerts) == len({a["id"] for a in alerts}) == len(details) > 0
    assert summary["queue_sample"]["n"] == len(alerts)
    for a in alerts:
        det = details[a["id"]]
        assert set(schema["model_features"]) == set(det["features"])
        limit = pd.Timestamp(det["evidence"]["decision_timestamp"])
        assert all(pd.Timestamp(t["timestamp"]) < limit for t in det["evidence"]["transactions"]), "future evidence"
        assert a["priority"] in {"P1", "P2", "P3"} and 0 <= a["score"] <= 1 and 0 <= a["p_cal"] <= 1
        assert "SYNTHETIC" in json.dumps(summary["disclosure"]).upper()
    assert summary["primary"]["n_positives"] > 0
    assert (d / "model" / "model_main.txt").exists() and (d / "model" / "stream.npz").exists()
