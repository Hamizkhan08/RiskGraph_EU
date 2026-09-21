#!/usr/bin/env python3
"""Run every quality gate and record the outcome in artifacts/qa_status.json.

    python scripts/run_qa.py [--frontend-dir frontend] [--live-api http://localhost:8010]

Each gate records: command, exit code, duration and a parsed summary. Nothing is marked passing unless it ran.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(name: str, cmd: str, cwd: Path, env: dict[str, str] | None = None, timeout: int = 900) -> dict:
    t = time.time()
    p = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout, env={**os.environ, **(env or {})}
    )
    tail = (p.stdout + p.stderr).strip().splitlines()[-3:]
    return {
        "gate": name,
        "cmd": cmd,
        "exit": p.returncode,
        "seconds": round(time.time() - t, 1),
        "ok": p.returncode == 0,
        "tail": [ln[:200] for ln in tail],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frontend-dir", default=str(ROOT / "frontend"))
    ap.add_argument("--live-api", default="")
    a = ap.parse_args()
    fe = Path(a.frontend_dir)
    out: dict = {"timestamp_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "gates": [], "counts": {}}
    g = out["gates"]
    g.append(run("ruff check", "ruff check .", ROOT))
    g.append(run("ruff format --check", "ruff format --check .", ROOT))
    g.append(
        run(
            "mypy",
            f"{sys.executable} -m mypy riskgraph backend/app scripts --ignore-missing-imports --explicit-package-bases",
            ROOT,
        )
    )
    g.append(run("pytest", f"{sys.executable} -m pytest --junitxml=/tmp/qa_junit.xml -q", ROOT))
    try:
        root = ET.parse("/tmp/qa_junit.xml").getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        if suite is None:
            raise ValueError("no testsuite element in junit report")
        out["counts"]["python"] = {k: int(suite.attrib[k]) for k in ("tests", "failures", "errors", "skipped")}
    except Exception as e:  # noqa: BLE001
        out["counts"]["python"] = {"error": str(e)}
    g.append(run("pip-audit (backend)", "pip-audit -r backend/requirements.txt", ROOT))
    g.append(run("eslint", "npx eslint", fe))
    g.append(run("tsc --noEmit", "npx tsc --noEmit", fe))
    env = {"LIVE_API_URL": a.live_api} if a.live_api else {}
    g.append(run("vitest", "npx vitest run --reporter=json --outputFile=/tmp/qa_vitest.json", fe, env))
    try:
        j = json.loads(Path("/tmp/qa_vitest.json").read_text())
        out["counts"]["frontend"] = {
            "tests": j["numTotalTests"],
            "passed": j["numPassedTests"],
            "failed": j["numFailedTests"],
            "skipped": j["numPendingTests"],
            "live_contract_included": bool(a.live_api),
        }
    except Exception as e:  # noqa: BLE001
        out["counts"]["frontend"] = {"error": str(e)}
    g.append(run("next build", "rm -rf .next && npx next build", fe))
    g.append(run("npm audit", "npm audit", fe))
    out["all_ok"] = all(x["ok"] for x in g)
    (ROOT / "artifacts" / "qa_status.json").write_text(json.dumps(out, indent=1))
    for x in g:
        print(f"{'PASS' if x['ok'] else 'FAIL'}  {x['gate']:22s} {x['seconds']:>6}s")
    print("counts:", out["counts"], "| all_ok:", out["all_ok"])


if __name__ == "__main__":
    main()
