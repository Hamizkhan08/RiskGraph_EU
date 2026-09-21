from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from . import __version__  # noqa: E402
from .api import router  # noqa: E402
from .security import RateLimiter, SecurityHeaders  # noqa: E402
from .settings import Settings  # noqa: E402
from .store import ArtifactStore, DecisionStore  # noqa: E402

log = logging.getLogger("riskgraph.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="RiskGraph EU API",
        version=__version__,
        description="Research prototype API (public/synthetic data). Not a detection system.",
        docs_url="/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.artifacts = ArtifactStore(settings.bundle_dir)
    app.state.decisions = DecisionStore(settings.db_path)
    app.state.sim_cache = {}
    app.add_middleware(SecurityHeaders)
    app.add_middleware(RateLimiter, per_minute=settings.rate_limit_per_min)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
        max_age=600,
    )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):  # never leak internals
        rid = uuid.uuid4().hex[:12]
        log.exception("unhandled error request_id=%s path=%s", rid, request.url.path)
        return JSONResponse({"detail": "internal server error", "request_id": rid}, status_code=500)

    app.include_router(router)
    return app
