#!/usr/bin/env python3
"""Build the application bundle (artifacts/demo) from finished runs and copy the browser-safe
part to frontend/public/demo.

    python scripts/build_bundle.py --li data/raw/tide_li --hi data/raw/tide_hi
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from riskgraph import config as C  # noqa: E402
from riskgraph.export import DISCLOSURE, LABELS, export_dataset  # noqa: E402
from riskgraph.runs import write_json  # noqa: E402

BROWSER_FILES = (
    "summary.json",
    "alerts.json",
    "case_details.json",
    "metrics.json",
    "monitoring.json",
    "data_quality.json",
    "manifest.json",
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--li", required=True)
    ap.add_argument("--hi", required=True)
    ap.add_argument("--runs", default=str(C.ARTIFACTS_DIR / "runs"))
    ap.add_argument("--out", default=str(C.ARTIFACTS_DIR / "demo"))
    ap.add_argument("--frontend", default=str(C.ROOT / "frontend" / "public" / "demo"))
    a = ap.parse_args()
    out, fe = Path(a.out), Path(a.frontend)
    info = []
    for key, data in (("LI", a.li), ("HI", a.hi)):
        run = Path(a.runs) / f"Tide-{key}-local-fv1-r1"
        info.append(export_dataset(run, Path(data), key, out / key))
        print("exported", info[-1])
    write_json(
        out / "index.json",
        {"datasets": [{"key": k, "label": LABELS[k]} for k in ("LI", "HI")], "default": "LI", "disclosure": DISCLOSURE},
    )
    fe.mkdir(parents=True, exist_ok=True)
    shutil.copy(out / "index.json", fe / "index.json")
    for key in ("LI", "HI"):
        (fe / key).mkdir(exist_ok=True)
        for f in BROWSER_FILES:
            shutil.copy(out / key / f, fe / key / f)
    print("bundle ->", out, "| browser copy ->", fe)


if __name__ == "__main__":
    main()
