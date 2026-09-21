from __future__ import annotations

import math
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request

from riskgraph.decision import PolicyConfig, boot_rates, simulate
from riskgraph.reasons import REASON_LABELS, reason_code

from . import __version__
from .schemas import CASE_ID, DecisionIn, DecisionOut, Health, Page, PredictIn, SimulateIn

DISCLOSURE = (
    "SYNTHETIC DATA — research prototype for alert prioritisation under limited review capacity. "
    "Not a detection system; not a replacement for AML investigators or compliance systems."
)
router = APIRouter()
PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}


def _state(request: Request):
    return request.app.state


def _bundle(request: Request, dataset: str):
    b = _state(request).artifacts.get(dataset)
    if b is None:
        raise HTTPException(404, f"dataset '{dataset}' is not available (bundle missing)")
    return b


def _case(request: Request, case_id: str):
    ds = case_id.split("-")[1]
    b = _bundle(request, ds)
    d = b.details.get(case_id)
    if d is None:
        raise HTTPException(404, "case not found")
    return ds, b, d


def _status(request: Request, ds: str, case_id: str) -> str:
    return _state(request).decisions.latest(ds).get(case_id, "open")


def require_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    key = _state(request).settings.api_key
    if key and x_api_key != key:
        raise HTTPException(401, "missing or invalid API key")


CaseId = Path(pattern=CASE_ID.pattern, description="Case identifier, e.g. RG-LI-1433-20251012")
DatasetQ = Query(default="LI", pattern="^(LI|HI)$")


@router.get("/health", response_model=Health)
def health(request: Request):
    st = _state(request)
    return Health(
        status="ok" if st.artifacts.ok else "degraded",
        version=__version__,
        demo_mode=st.settings.demo_mode,
        datasets=sorted(st.artifacts.bundles),
        model_loaded=st.artifacts.model_loaded(),
        disclosure=DISCLOSURE,
    )


@router.get("/api/datasets")
def datasets(request: Request) -> dict[str, Any]:
    st = _state(request)
    return {
        "datasets": st.artifacts.index.get("datasets", []),
        "default": st.artifacts.index.get("default", "LI"),
        "demo_mode": st.settings.demo_mode,
        "disclosure": DISCLOSURE,
    }


@router.get("/api/dashboard")
def dashboard(request: Request, dataset: str = DatasetQ) -> dict[str, Any]:
    b = _bundle(request, dataset)
    latest = _state(request).decisions.latest(dataset)
    alerts = b.alerts
    by: dict[str, int] = {}
    for d in latest.values():
        by[d] = by.get(d, 0) + 1
    decided = sum(1 for a in alerts if a["id"] in latest)
    recent = sorted(alerts, key=lambda a: (a["date"], a["score"]), reverse=True)[:8]
    return {
        "summary": b.summary,
        "decisions": {
            "by_decision": by,
            "decided_in_sample": decided,
            "open_in_sample": len(alerts) - decided,
            "sample_size": len(alerts),
            "simulated": _state(request).settings.demo_mode,
        },
        "latest_alerts": [{**a, "status": latest.get(a["id"], "open")} for a in recent],
        "disclosure": DISCLOSURE,
    }


@router.get("/api/alerts", response_model=Page)
def alerts(
    request: Request,
    dataset: str = DatasetQ,
    q: str = Query(default="", max_length=64),
    priority: str = Query(default="", pattern="^(P1|P2|P3)?$"),
    status: str = Query(default="", pattern="^(open|suspicious|false_positive|requires_review)?$"),
    sort: str = Query(default="date", pattern="^(date|score|priority|amount)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=25, ge=1, le=100),
):
    b = _bundle(request, dataset)
    latest = _state(request).decisions.latest(dataset)
    items = [{**a, "status": latest.get(a["id"], "open")} for a in b.alerts]
    ql = q.strip().lower()
    if ql:
        items = [
            a for a in items if ql in a["id"].lower() or ql in a["account"].lower() or ql in a["key_reason"].lower()
        ]
    if priority:
        items = [a for a in items if a["priority"] == priority]
    if status:
        items = [a for a in items if a["status"] == status]
    keyf = {
        "date": lambda a: (a["date"], a["score"]),
        "score": lambda a: a["score"],
        "priority": lambda a: (PRIORITY_ORDER[a["priority"]], -a["score"]),
        "amount": lambda a: a["amounts"]["out_7d"] + a["amounts"]["in_7d"],
    }[sort]
    items.sort(key=keyf, reverse=(order == "desc"))
    total = len(items)
    lo = (page - 1) * page_size
    return Page(items=items[lo : lo + page_size], total=total, page=page, page_size=page_size, disclosure=DISCLOSURE)


@router.get("/api/alerts/{case_id}")
def alert(request: Request, case_id: str = CaseId) -> dict[str, Any]:
    ds, b, d = _case(request, case_id)
    light = next(a for a in b.alerts if a["id"] == case_id)
    return {**light, "status": _status(request, ds, case_id)}


@router.get("/api/cases", response_model=Page)
def cases(
    request: Request,
    dataset: str = DatasetQ,
    all: bool = False,
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=25, ge=1, le=100),
):
    b = _bundle(request, dataset)
    latest = _state(request).decisions.latest(dataset)
    items = [{**a, "status": latest.get(a["id"], "open")} for a in b.alerts if all or a["id"] in latest]
    items.sort(key=lambda a: a["date"], reverse=True)
    lo = (page - 1) * page_size
    return Page(
        items=items[lo : lo + page_size], total=len(items), page=page, page_size=page_size, disclosure=DISCLOSURE
    )


@router.get("/api/cases/{case_id}")
def case(request: Request, case_id: str = CaseId) -> dict[str, Any]:
    ds, b, d = _case(request, case_id)
    hist = _state(request).decisions.history(case_id)
    return {
        **d,
        "status": hist[-1]["decision"] if hist else "open",
        "decision_history": hist,
        "simulated_feedback": _state(request).settings.demo_mode,
        "disclosure": DISCLOSURE,
    }


@router.get("/api/network/{case_id}")
def network(request: Request, case_id: str = CaseId) -> dict[str, Any]:
    _, _, d = _case(request, case_id)
    ev = d["evidence"]
    return {
        "case_id": case_id,
        "focal": ev["focal"],
        "nodes": ev["nodes"],
        "edges": ev["edges"],
        "lookback_days": ev["lookback_days"],
        "decision_timestamp": ev["decision_timestamp"],
        "counterparties_total": ev["counterparties_total"],
        "disclosure": DISCLOSURE,
    }


@router.get("/api/explanations/{case_id}")
def explanation(request: Request, case_id: str = CaseId) -> dict[str, Any]:
    _, _, d = _case(request, case_id)
    return {
        "case_id": case_id,
        "score": d["score"],
        "p_cal": d["p_cal"],
        **d["explanation"],
        "transactions": d["evidence"]["transactions"],
        "features": d["features"],
        "research": d["research"],
        "method": "TreeSHAP (LightGBM pred_contrib, log-odds); reason codes group features only",
        "disclosure": DISCLOSURE,
    }


@router.post(
    "/api/cases/{case_id}/decision", response_model=DecisionOut, dependencies=[Depends(require_key)], status_code=201
)
def decide(request: Request, body: DecisionIn, case_id: str = CaseId):
    ds, _, _ = _case(request, case_id)
    st = _state(request)
    rec = st.decisions.add(case_id, ds, body.decision, body.note, body.analyst, st.settings.demo_mode)
    return DecisionOut(**rec, status=body.decision)


@router.get("/api/model/metrics")
def model_metrics(request: Request, dataset: str = DatasetQ) -> dict[str, Any]:
    return _bundle(request, dataset).metrics


@router.get("/api/model/calibration")
def model_calibration(request: Request, dataset: str = DatasetQ) -> dict[str, Any]:
    b = _bundle(request, dataset)
    return {
        "dataset": dataset,
        "models": b.metrics["h1"]["calibration"],
        "pr_curve_main": b.metrics["h1"]["pr_curve_main"],
        "windows": b.monitoring["calibration_windows"],
        "calibration_policy": b.manifest["calibration"],
        "disclosure": DISCLOSURE,
    }


@router.get("/api/monitoring")
def monitoring(request: Request, dataset: str = DatasetQ) -> dict[str, Any]:
    return _bundle(request, dataset).monitoring


@router.get("/api/data-quality")
def data_quality(request: Request, dataset: str = DatasetQ) -> dict[str, Any]:
    b = _bundle(request, dataset)
    return {**b.data_quality, "provenance": b.manifest["dataset"], "disclosure": DISCLOSURE}


@router.post("/api/predict")
def predict(request: Request, body: PredictIn, dataset: str = DatasetQ) -> dict[str, Any]:
    b = _bundle(request, dataset)
    cols = b.schema["model_features"]
    missing = [c for c in cols if c not in body.features]
    extra = [c for c in body.features if c not in cols]
    if missing or extra:
        raise HTTPException(422, {"missing": missing[:20], "unknown": extra[:20], "expected_n": len(cols)})
    x = np.array([[body.features[c] for c in cols]], dtype=float)
    raw = float(b.booster.predict(x)[0])
    contrib = b.booster.predict(x, pred_contrib=True)[0]
    z = float(np.log(np.clip(raw, 1e-6, 1 - 1e-6) / (1 - np.clip(raw, 1e-6, 1 - 1e-6))))
    cal = b.calibration
    p_cal = 1.0 / (1.0 + math.exp(-(cal["coef"] * z + cal["intercept"])))
    order = np.argsort(-np.abs(contrib[:-1]))[:8]
    grouped: dict[str, float] = {}
    for c, v in zip(cols, contrib[:-1]):
        grouped[reason_code(c)] = grouped.get(reason_code(c), 0.0) + float(v)
    return {
        "score": raw,
        "p_cal": p_cal,
        "base_value": float(contrib[-1]),
        "contributions": [
            {
                "feature": cols[j],
                "value": float(x[0, j]),
                "contribution": float(contrib[j]),
                "group": b.schema["features"][cols[j]]["group"],
                "reason_code": reason_code(cols[j]),
            }
            for j in order
        ],
        "reasons": [
            {"code": k, "label": REASON_LABELS[k], "contribution": v}
            for k, v in sorted(grouped.items(), key=lambda kv: -abs(kv[1]))[:4]
        ],
        "run_id": b.manifest["run_id"],
        "disclosure": DISCLOSURE,
        "note": "Elevated-risk score for research use; not a determination of criminal activity.",
    }


@router.post("/api/simulate")
def simulate_policy(request: Request, body: SimulateIn) -> dict[str, Any]:
    st = _state(request)
    if not st.settings.simulate_enabled:
        raise HTTPException(503, "simulation disabled")
    b = _bundle(request, body.dataset)
    key = (body.dataset, body.policy, round(body.alpha, 4), round(body.capacity_multiplier, 3), body.label_regime)
    cache: dict = st.sim_cache
    if key in cache:
        return cache[key]
    s = b.stream
    res = simulate(
        s["day"].astype(int),
        s["score"].astype(float),
        s["y"].astype(int),
        r=float(body.capacity_multiplier * float(s["p_train"])),
        policy=PolicyConfig(kind=body.policy, alpha=body.alpha, label_regime=body.label_regime),
        cal_scores=s["cal_score"].astype(float),
        cal_days=s["cal_day"].astype(int),
        family_mask=s["fm"].astype(int),
        cluster=s["sch"].astype(int),
    )
    cc = res.pop("cluster_counts", None)
    ser = res.pop("series")
    res.pop("weekly_miss", None)
    out = {
        **res,
        "miss_ci95": boot_rates(cc, "n_closed") if cc else None,
        "unreviewed_rate": 1 - res["review_recall"],
        "series": {k: ser[k] for k in ("day", "review", "auto_close", "backlog")},
        "dataset": body.dataset,
        "capacity_multiplier": body.capacity_multiplier,
        "note": "Computed live from the stored test-window score stream (synthetic data).",
        "disclosure": DISCLOSURE,
    }
    if len(cache) > 200:
        cache.clear()
    cache[key] = out
    return out


@router.get("/api/audit")
def audit(request: Request, _: None = Depends(require_key)) -> dict[str, Any]:
    return {"events": _state(request).decisions.audit(), "disclosure": DISCLOSURE}
