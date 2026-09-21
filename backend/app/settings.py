from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _b(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    """All configuration comes from RISKGRAPH_* environment variables. No secret has a default."""

    bundle_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("RISKGRAPH_BUNDLE_DIR", ROOT / "artifacts" / "demo"))
    )
    db_path: str = field(
        default_factory=lambda: os.environ.get("RISKGRAPH_DB_PATH", str(ROOT / "riskgraph_decisions.db"))
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip() for o in os.environ.get("RISKGRAPH_CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
        )
    )
    demo_mode: bool = field(default_factory=lambda: _b("RISKGRAPH_DEMO_MODE", True))
    rate_limit_per_min: int = field(default_factory=lambda: int(os.environ.get("RISKGRAPH_RATE_LIMIT_PER_MIN", "120")))
    api_key: str | None = field(default_factory=lambda: os.environ.get("RISKGRAPH_API_KEY") or None)
    simulate_enabled: bool = field(default_factory=lambda: _b("RISKGRAPH_SIMULATE_ENABLED", True))
