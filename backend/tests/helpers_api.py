"""Shared backend test helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.settings import Settings

COLS = ["t_n_out_1d", "t_n_in_1d", "t_amt_out_1d", "g_deg_und_7d", "m_cycle3_7d"]
IDS = [f"RG-LI-{1400 + i}-2025101{i}" for i in range(6)]


def _detail(i: int, cid: str) -> dict:
    light = {
        "id": cid,
        "dataset": "LI",
        "account": f"account_{1400 + i}",
        "date": f"2025-10-1{i}",
        "decision_timestamp": f"2025-10-1{i + 1}T00:00:00",
        "score": 0.9 - 0.1 * i,
        "p_cal": 0.05 - 0.005 * i,
        "priority": ["P1", "P1", "P2", "P2", "P3", "P3"][i],
        "status": "open",
        "key_reason": "Elevated transfer activity",
        "key_reason_code": "TRANSFER_ACTIVITY",
        "network": {
            "degree_7d": 3.0 + i,
            "reach2_7d": 9.0,
            "hub_neighbour_share": 0.1,
            "cycles": {"c2": 0.0, "c3": float(i == 0), "c4": 0.0},
            "fanin_burst_3d": 1.0,
            "fanout_burst_3d": 2.0,
        },
        "amounts": {
            "out_1d": 100.0 * (i + 1),
            "in_1d": 10.0,
            "out_7d": 300.0 * (i + 1),
            "in_7d": 50.0,
            "n_tx_1d": 3.0,
            "note": "nominal units",
        },
    }
    return {
        **light,
        "explanation": {
            "base_value": -7.0,
            "margin": -3.0,
            "top_features": [
                {
                    "feature": "t_n_out_1d",
                    "value": 2.0,
                    "contribution": 1.5,
                    "group": "T",
                    "definition": "d",
                    "reason_code": "ACTIVITY_VOLUME",
                }
            ],
            "reasons": [{"code": "TRANSFER_ACTIVITY", "label": "Elevated transfer activity", "contribution": 1.5}],
        },
        "evidence": {
            "focal": light["account"],
            "decision_timestamp": light["decision_timestamp"],
            "lookback_days": 7,
            "transactions": [
                {
                    "timestamp": "2025-10-10T09:00:00",
                    "src": light["account"],
                    "dst": "account_9",
                    "amount": 100.0,
                    "currency": "EUR",
                    "type": "transfer",
                    "direction": "out",
                }
            ],
            "n_transactions_window": 1,
            "counterparties_total": 1,
            "nodes": [
                {"id": light["account"], "focal": True, "n": 1, "amount": 100.0},
                {"id": "account_9", "focal": False, "n": 1, "amount": 100.0},
            ],
            "edges": [
                {
                    "source": light["account"],
                    "target": "account_9",
                    "n": 1,
                    "amount": 100.0,
                    "first": "2025-10-10T09:00:00",
                    "last": "2025-10-10T09:00:00",
                }
            ],
        },
        "features": {c: 1.0 for c in COLS},
        "research": {"ground_truth_positive": int(i % 2 == 0), "family": None, "scheme_id": None, "note": "synthetic"},
    }


def make_client(bundle_dir: Path, tmp_path: Path, **kw) -> TestClient:
    s = Settings(
        bundle_dir=bundle_dir,
        db_path=str(tmp_path / "t.db"),
        cors_origins=("http://localhost:3000",),
        demo_mode=kw.get("demo_mode", True),
        rate_limit_per_min=kw.get("rate", 10_000),
        api_key=kw.get("api_key"),
        simulate_enabled=True,
    )
    return TestClient(create_app(s), raise_server_exceptions=False)
