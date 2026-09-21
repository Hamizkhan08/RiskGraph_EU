#!/usr/bin/env python3
"""Run H1/H2/H3 on one Tide-format dataset directory and write artifacts/runs/<run_id>/.

python scripts/run_experiments.py --data data/raw/tide_li [--seeds 11 23 37]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from riskgraph import config as C  # noqa: E402
from riskgraph import experiments as E  # noqa: E402
from riskgraph.data.schema import validate_transactions  # noqa: E402
from riskgraph.data.tide import load_tide  # noqa: E402
from riskgraph.runs import make_manifest, write_json  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(C.SEEDS))
    ap.add_argument("--out", default=str(C.ARTIFACTS_DIR / "runs"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    seeds = tuple(a.seeds)
    td = load_tide(a.data)
    dq = validate_transactions(td)
    prep = E.prepare(td, cache=C.DATA_DIR / "interim")
    manifest = make_manifest(prep, seeds)
    out = Path(a.out) / manifest["run_id"]
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    sc_path = out / "scores_h1.npz"
    if sc_path.exists() and (out / "h1.json").exists():
        z = np.load(sc_path)
        scores = {(k.split("__")[0], int(k.split("__")[1])): z[k] for k in z.files if k != "rows"}
        logging.info("resumed H1 scores from %s", sc_path)
    else:
        h1, scores, models = E.stage_h1(prep, seeds)
        write_json(out / "h1.json", h1)
        np.savez_compressed(sc_path, rows=prep.rows, **{f"{n}__{s}": v for (n, s), v in scores.items()})
        models[(E.MAIN, seeds[0])].booster.save_model(str(out / "model_main.txt"))
        logging.info("H1 done (%.0fs)", time.time() - t0)
    hp = out / "scores_h2.npz"
    if hp.exists() and (out / "h2.json").exists():
        z = np.load(hp)
        held = {(int(k.split("__")[1]), k.split("__")[2], int(k.split("__")[3])): z[k] for k in z.files}
        logging.info("resumed H2 scores")
    else:
        h2, held = E.stage_h2(prep, scores, seeds)
        write_json(out / "h2.json", h2)
        np.savez_compressed(hp, **{f"held__{f}__{n}__{s}": v for (f, n, s), v in held.items()})
        logging.info("H2 done (%.0fs)", time.time() - t0)
    h3 = E.stage_h3(prep, scores, held, seeds)
    write_json(out / "h3.json", h3)
    logging.info("H3 done (%.0fs)", time.time() - t0)
    write_json(out / "manifest.json", manifest)
    write_json(out / "data_quality.json", dq)
    logging.info("all done in %.0fs -> %s", time.time() - t0, out)


if __name__ == "__main__":
    main()
