from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Dataset = Literal["LI", "HI"]
Decision = Literal["suspicious", "false_positive", "requires_review"]
CASE_ID = re.compile(r"^RG-(LI|HI)-\d{1,6}-\d{8}$")


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    demo_mode: bool
    datasets: list[str]
    model_loaded: bool
    disclosure: str


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Decision
    note: str = Field(default="", max_length=500)
    analyst: str = Field(default="demo-analyst", min_length=1, max_length=40, pattern=r"^[A-Za-z0-9 ._-]+$")


class DecisionOut(BaseModel):
    case_id: str
    decision: Decision
    note: str
    analyst: str
    simulated: bool
    created_at: str
    status: str


class PredictIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: dict[str, float]

    @field_validator("features")
    @classmethod
    def finite(cls, v: dict[str, float]) -> dict[str, float]:
        import math

        if len(v) > 200:
            raise ValueError("too many features")
        bad = [k for k, x in v.items() if not math.isfinite(x)]
        if bad:
            raise ValueError(f"non-finite values: {bad[:5]}")
        return v


class SimulateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: Dataset = "LI"
    policy: Literal["none", "static", "rolling", "conformal"] = "static"
    alpha: float = Field(default=0.10, gt=0.0, le=0.5)
    capacity_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)
    label_regime: Literal["oracle", "review_only"] = "oracle"


class Page(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    disclosure: str
