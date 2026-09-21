#!/usr/bin/env python3
"""Generate a Tide-format dataset locally with the MIT-licensed Tide generator.

    git clone https://github.com/mntijn/Tide.git ../Tide
    python scripts/generate_tide.py --tide ../Tide --variant li --out data/raw/tide_li

Reduced scale (default 1500 individuals) so it fits in ~2.3 GB RAM. Pattern counts keep the
repository's LI:HI ratio (180:320 ~ 1:1.78). This is NOT the Zenodo release (10.5281/zenodo.18804069);
its licence was not verified and it is not used.
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404 - CLI run by the user; arguments are passed as a list, never through a shell
import sys
from pathlib import Path

import yaml

VARIANTS = {"li": (60, 0.0005), "hi": (107, 0.0009)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tide", required=True, help="path to a clone of mntijn/Tide")
    ap.add_argument("--variant", choices=VARIANTS, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--individuals", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    tide, out = Path(a.tide), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load((tide / "configs" / "graph.yaml").read_text())
    patterns, ratio = VARIANTS[a.variant]
    cfg["graph_scale"]["individuals"] = a.individuals
    cfg["pattern_frequency"]["num_illicit_patterns"] = patterns
    cfg["target_fraud_ratio"] = ratio
    cfg["random_seed"] = a.seed
    cfg_path = out / "graph_config_used.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    subprocess.run(  # nosec B603
        [sys.executable, "main.py", "--config", str(cfg_path.resolve()), "--output-dir", str(out.resolve())],
        cwd=tide,
        check=True,
    )
    commit = subprocess.run(  # nosec B603 B607 - fixed git command, path from the local user
        ["git", "-C", str(tide), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    (out / "dataset_meta.json").write_text(
        json.dumps(
            {
                "name": f"Tide-{a.variant.upper()}-local",
                "generator": "mntijn/Tide (MIT)",
                "generator_commit": commit,
                "seed": a.seed,
                "start_date": cfg["time_span"]["start_date"][:10],
                "period_days": 365,
                "config": {"individuals": a.individuals, "num_illicit_patterns": patterns, "target_fraud_ratio": ratio},
                "source_note": "locally generated Tide-format data at reduced scale (NOT the Zenodo release)",
            },
            indent=2,
        )
    )
    print("done:", out)


if __name__ == "__main__":
    main()
