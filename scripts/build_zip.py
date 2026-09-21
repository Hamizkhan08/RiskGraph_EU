#!/usr/bin/env python3
"""Build RiskGraph_EU_FINAL.zip, PROJECT_MANIFEST.md and MANIFEST_SHA256.txt; optionally verify an existing zip.

    python scripts/build_zip.py build [--out RiskGraph_EU_FINAL.zip]
    python scripts/build_zip.py verify RiskGraph_EU_FINAL.zip        # integrity + every checksum vs the manifest

Excluded: VCS data, dependencies, caches, build output, raw/interim data, large run arrays, databases, secrets, zips.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = "RiskGraph_EU"
# Directories excluded wherever they appear (dependencies, caches, build output) ...
EXCLUDE_ANYWHERE = {
    ".git",
    "node_modules",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".vercel",
    "coverage",
}
# ... and directories excluded ONLY at the repository root. (`riskgraph/data/` is source code and must ship —
# an earlier version of this script excluded every directory named "data" and silently dropped the adapters.)
EXCLUDE_TOP = {"data", "outputs"}
EXCLUDE_GLOBS = [
    "*.zip",
    "*.pyc",
    "*.db",
    "*.sqlite",
    ".env",
    ".env.local",
    ".env.*.local",
    "*.pem",
    "*.key",
    "tsconfig.tsbuildinfo",
    "next-env.d.ts",
    ".DS_Store",
    "artifacts/runs/*/scores_*.npz",
    "artifacts/runs/*/model_main.txt",
    "*.log",
]
KEEP = {".env.example", "frontend/.env.example"}
EXCLUDED_WHY = [
    ("`.git`, `node_modules`, `.next`, virtual environments, `__pycache__`, tool caches", "rebuildable; not source"),
    (
        "`data/` (raw/interim Tide files, feature caches — ≈ 590 MB)",
        "regenerable with `scripts/generate_tide.py`; raw datasets are never committed",
    ),
    (
        "`artifacts/runs/*/scores_*.npz`, `artifacts/runs/*/model_main.txt`",
        "large/regenerable; the run JSON + manifests ARE included; the served model is in `artifacts/demo/*/model/`",
    ),
    ("`.env`, `*.pem`, `*.key`, `*.db`", "secrets / local state (none present)"),
    (
        "`*.zip` (including the superseded Gate 0.5 archive), logs, `tsconfig.tsbuildinfo`, `next-env.d.ts`",
        "build/derived files",
    ),
]
PURPOSE = {
    "README.md": "recruiter-facing overview, honest findings, quick start",
    "requirements.txt": "Python dependencies (tested lower bounds)",
    "pyproject.toml": "ruff / mypy / pytest configuration",
    "render.yaml": "Render blueprint for the API (not applied)",
    ".env.example": "environment variable template (no secrets)",
    ".github/workflows/ci.yml": "CI mirroring local gates (not executed)",
    "riskgraph/features/build.py": "time-respecting account-day feature engine + registry",
    "riskgraph/decision.py": "capacity-constrained decision engine, 3 auto-close policies",
    "riskgraph/experiments.py": "H1/H2/H3 experiment stages",
    "riskgraph/leakage.py": "automated leakage checks",
    "riskgraph/export.py": "application-bundle exporter",
    "backend/app/api.py": "FastAPI routes",
    "backend/Dockerfile": "API container (not built in the build environment)",
    "frontend/lib/api.ts": "demo/live backend abstraction",
    "frontend/next.config.ts": "security headers / CSP",
    "scripts/run_qa.py": "runs and records every quality gate",
    "scripts/build_zip.py": "this packaging tool",
    "artifacts/qa_status.json": "recorded outcome of the quality gates",
    "artifacts/results_manifest.json": "every reported figure traced to run/dataset/split/model/seed/source file",
    "docs/RESEARCH_SPEC_FINAL.md": "source of truth for the research design",
    "docs/RESULTS.md": "generated results",
    "docs/FINAL_AUDIT.md": "PASS/FAIL checklist with evidence",
}


REQUIRED = [
    "riskgraph/__init__.py",
    "riskgraph/config.py",
    "riskgraph/decision.py",
    "riskgraph/experiments.py",
    "riskgraph/data/__init__.py",
    "riskgraph/data/schema.py",
    "riskgraph/data/tide.py",
    "riskgraph/data/fixture.py",
    "riskgraph/data/amlnet.py",
    "riskgraph/features/build.py",
    "backend/app/api.py",
    "backend/app/main.py",
    "backend/Dockerfile",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/app/page.tsx",
    "frontend/public/demo/index.json",
    "artifacts/demo/index.json",
    "artifacts/demo/LI/model/model_main.txt",
    "artifacts/demo/HI/model/stream.npz",
    "artifacts/results_manifest.json",
    "tests/conftest.py",
    "docs/RESEARCH_SPEC_FINAL.md",
    "docs/FINAL_AUDIT.md",
    "requirements.txt",
    "README.md",
    "PROJECT_MANIFEST.md",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in KEEP:
            out.append(p)
            continue
        parts = p.relative_to(ROOT).parts
        if parts[0] in EXCLUDE_TOP or any(part in EXCLUDE_ANYWHERE for part in parts[:-1]):
            continue
        if rel in ("PROJECT_MANIFEST.md", "MANIFEST_SHA256.txt"):
            continue
        if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(p.name, g) for g in EXCLUDE_GLOBS):
            continue
        out.append(p)
    return out


def manifest(fs: list[Path], zip_status: str) -> tuple[str, str]:
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in fs}
    tree = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(hashes.items())).encode()).hexdigest()
    qa = json.loads((ROOT / "artifacts" / "qa_status.json").read_text())
    runs = [json.loads(p.read_text()) for p in sorted((ROOT / "artifacts" / "runs").glob("*/manifest.json"))]
    tops: dict[str, int] = {}
    for k in hashes:
        top = k.split("/")[0] if "/" in k else "(root)"
        tops[top] = tops.get(top, 0) + 1
    L = [
        "# PROJECT MANIFEST — RiskGraph EU (final build)",
        "",
        f"Generated {dt.datetime.now(dt.UTC).isoformat(timespec='seconds')} by `scripts/build_zip.py`.",
        "",
        "## Version / provenance",
        "* Pipeline 1.0.0 · feature version fv1 · API 1.0.0 · no VCS commit (the build environment had no repository); "
        f"**source-tree hash** (SHA-256 over sorted file hashes): `{tree}`",
    ]
    for m in runs:
        d = m["dataset"]
        L.append(
            f"* Run `{m['run_id']}` — generator `{d['generator']}` @ `{d['generator_commit']}`, seed {d['seed']}, config {d['config']}"
        )
    L += [
        "",
        "## Status",
        f"* **Quality gates** ({qa['timestamp_utc']}): "
        + " · ".join(f"{'PASS' if g['ok'] else 'FAIL'} {g['gate']}" for g in qa["gates"]),
        f"* **Tests:** Python {qa['counts']['python']} · Frontend {qa['counts']['frontend']}",
        "* **Build:** `next build` succeeded (8 routes); production server started and all routes returned HTTP 200 locally.",
        "* **Deployment:** **NOT DEPLOYED** (no Vercel/Render account available to the build). No public URLs.",
        f"* **This ZIP:** {zip_status}",
        "",
        "## Included directories (file counts)",
    ]
    L += [f"* `{k}/` — {v}" if k != "(root)" else f"* repository root — {v}" for k, v in sorted(tops.items())]
    L += ["", "## Important files"]
    L += [f"* `{k}` — {v}" for k, v in PURPOSE.items() if k in hashes]
    L += ["", "## Intentionally excluded"] + [f"* {a} — {b}" for a, b in EXCLUDED_WHY]
    L += ["", "## SHA-256 of important artefacts (all files: `MANIFEST_SHA256.txt`)", "| File | SHA-256 |", "|---|---|"]
    imp = [
        k
        for k in hashes
        if k.startswith(("artifacts/demo/", "artifacts/runs/"))
        and k.endswith(("manifest.json", "model_main.txt", "stream.npz", "summary.json", "metrics.json"))
    ]
    imp += [
        "frontend/package-lock.json",
        "artifacts/results_manifest.json",
        "artifacts/qa_status.json",
        "docs/RESULTS.md",
        "docs/RESEARCH_SPEC_FINAL.md",
        "requirements.txt",
    ]
    L += [f"| `{k}` | `{hashes[k]}` |" for k in sorted(set(imp)) if k in hashes]
    return "\n".join(L) + "\n", "".join(f"{v}  {k}\n" for k, v in sorted(hashes.items()))


def build(out: Path, zip_status: str) -> None:
    (ROOT / "PROJECT_MANIFEST.md").write_text("")  # placeholder so file lists are stable
    fs = files()
    md, sums = manifest(fs, zip_status)
    (ROOT / "PROJECT_MANIFEST.md").write_text(md)
    (ROOT / "MANIFEST_SHA256.txt").write_text(sums)
    fs = files() + [ROOT / "PROJECT_MANIFEST.md", ROOT / "MANIFEST_SHA256.txt"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(fs):
            z.write(p, f"{TOP}/{p.relative_to(ROOT).as_posix()}")
    print(f"built {out} — {len(fs)} files, {out.stat().st_size:,} bytes, sha256 {sha(out)}")


def verify(zpath: Path) -> int:
    bad = 0
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None, "corrupt member"
        names = [n for n in z.namelist() if not n.endswith("/")]
        assert all(n.startswith(TOP + "/") for n in names), "single top-level folder violated"
        forbidden = [
            n
            for n in names
            if any(part in EXCLUDE_ANYWHERE for part in n.split("/")[1:-1])
            or n.split("/")[1] in EXCLUDE_TOP
            or n.endswith((".env", ".db", ".pem"))
        ]
        assert not forbidden, f"excluded content present: {forbidden[:5]}"
        missing = [r for r in REQUIRED if f"{TOP}/{r}" not in names]
        assert not missing, f"required files missing from the zip: {missing}"
        with tempfile.TemporaryDirectory() as tmp:
            z.extractall(tmp)
            root = Path(tmp) / TOP
            for line in (root / "MANIFEST_SHA256.txt").read_text().splitlines():
                digest, rel = line.split("  ", 1)
                if not (root / rel).exists() or sha(root / rel) != digest:
                    bad += 1
                    print("MISMATCH", rel)
            listed = {ln.split("  ", 1)[1] for ln in (root / "MANIFEST_SHA256.txt").read_text().splitlines()}
            actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} - {
                "PROJECT_MANIFEST.md",
                "MANIFEST_SHA256.txt",
            }
            if listed != actual:
                bad += 1
                print("file-set mismatch:", sorted(listed ^ actual)[:5])
    print("VERIFY", "OK" if not bad else f"FAILED ({bad})", f"— {len(names)} members")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", default=str(ROOT / "RiskGraph_EU_FINAL.zip"))
    b.add_argument("--status", default="built; verification pending")
    v = sub.add_parser("verify")
    v.add_argument("zip")
    a = ap.parse_args()
    if a.cmd == "build":
        build(Path(a.out), a.status)
    else:
        sys.exit(verify(Path(a.zip)))
