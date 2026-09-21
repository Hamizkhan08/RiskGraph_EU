from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import Any


class Bundle:
    """One dataset's artifacts (produced offline by scripts/build_bundle.py). Read-only."""

    def __init__(self, path: Path):
        self.path = path

    def _j(self, name: str) -> Any:
        return json.loads((self.path / name).read_text())

    @cached_property
    def summary(self) -> dict:
        return self._j("summary.json")

    @cached_property
    def alerts(self) -> list[dict]:
        return self._j("alerts.json")

    @cached_property
    def details(self) -> dict[str, dict]:
        return self._j("case_details.json")

    @cached_property
    def metrics(self) -> dict:
        return self._j("metrics.json")

    @cached_property
    def monitoring(self) -> dict:
        return self._j("monitoring.json")

    @cached_property
    def data_quality(self) -> dict:
        return self._j("data_quality.json")

    @cached_property
    def manifest(self) -> dict:
        return self._j("manifest.json")

    @cached_property
    def schema(self) -> dict:
        return self._j("model/feature_schema.json")

    @cached_property
    def calibration(self) -> dict:
        return self._j("model/calibration.json")

    @cached_property
    def booster(self):
        import lightgbm as lgb

        return lgb.Booster(model_file=str(self.path / "model" / "model_main.txt"))

    @cached_property
    def stream(self) -> dict:
        import numpy as np

        z = np.load(self.path / "model" / "stream.npz")
        return {k: z[k] for k in z.files}


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root
        self.index: dict = {}
        self.bundles: dict[str, Bundle] = {}
        idx = root / "index.json"
        if idx.exists():
            self.index = json.loads(idx.read_text())
            for d in self.index.get("datasets", []):
                if (root / d["key"] / "summary.json").exists():
                    self.bundles[d["key"]] = Bundle(root / d["key"])

    @property
    def ok(self) -> bool:
        return bool(self.bundles)

    def get(self, key: str) -> Bundle | None:
        return self.bundles.get(key)

    def model_loaded(self) -> bool:
        return all((b.path / "model" / "model_main.txt").exists() for b in self.bundles.values()) and self.ok


class DecisionStore:
    """Analyst decisions + audit events (SQLite, parameterised queries only)."""

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS decisions(
              id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, dataset TEXT NOT NULL,
              decision TEXT NOT NULL CHECK(decision IN ('suspicious','false_positive','requires_review')),
              note TEXT NOT NULL DEFAULT '', analyst TEXT NOT NULL, simulated INTEGER NOT NULL,
              created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_decisions_case ON decisions(case_id, id);
            CREATE INDEX IF NOT EXISTS idx_decisions_dataset ON decisions(dataset);
            CREATE TABLE IF NOT EXISTS audit_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, event TEXT NOT NULL,
              case_id TEXT, detail TEXT NOT NULL DEFAULT '');
            """)

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def add(self, case_id: str, dataset: str, decision: str, note: str, analyst: str, simulated: bool) -> dict:
        ts = self.now()
        with self.lock:
            self.conn.execute(
                "INSERT INTO decisions(case_id,dataset,decision,note,analyst,simulated,created_at) VALUES(?,?,?,?,?,?,?)",
                (case_id, dataset, decision, note, analyst, int(simulated), ts),
            )
            self.conn.execute(
                "INSERT INTO audit_events(ts,event,case_id,detail) VALUES(?,?,?,?)",
                (ts, "decision_recorded", case_id, decision),
            )
            self.conn.commit()
        return {
            "case_id": case_id,
            "decision": decision,
            "note": note,
            "analyst": analyst,
            "simulated": simulated,
            "created_at": ts,
        }

    def history(self, case_id: str) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT decision,note,analyst,simulated,created_at FROM decisions WHERE case_id=? ORDER BY id",
                (case_id,),
            ).fetchall()
        return [
            {"decision": r[0], "note": r[1], "analyst": r[2], "simulated": bool(r[3]), "created_at": r[4]} for r in rows
        ]

    def latest(self, dataset: str) -> dict[str, str]:
        with self.lock:
            rows = self.conn.execute(
                """SELECT case_id, decision FROM decisions WHERE dataset=? AND id IN
                                        (SELECT MAX(id) FROM decisions WHERE dataset=? GROUP BY case_id)""",
                (dataset, dataset),
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def audit(self, limit: int = 50) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT ts,event,case_id,detail FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"ts": r[0], "event": r[1], "case_id": r[2], "detail": r[3]} for r in rows]
