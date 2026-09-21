import math

import numpy as np
import pytest

from riskgraph.decision import PolicyConfig, conformal_tau, empirical_tau, simulate


def make_stream(n_days=30, per_day=400, prev=0.5, seed=0, pos_ab=(5, 2)):
    rng = np.random.default_rng(seed)
    day = np.repeat(np.arange(n_days), per_day)
    y = (rng.random(len(day)) < prev).astype(int)
    score = np.where(y == 1, rng.beta(*pos_ab, len(day)), rng.beta(2, 5, len(day)))
    return day, score, y


def cal(seed=99, n=2000, ab=(5, 2)):
    return np.random.default_rng(seed).beta(*ab, n)


def test_zones_are_exclusive_and_exhaustive():
    day, s, y = make_stream(prev=0.05)
    res = simulate(day, s, y, r=0.05, policy=PolicyConfig("static", 0.1), cal_scores=cal(), return_zone=True)
    z = res["zone"]
    assert set(np.unique(z)) <= {1, 2, 3, 4} and (z > 0).all()
    ser = res["series"]
    assert (z == 1).sum() == sum(ser["review"]) and (z == 2).sum() == sum(ser["auto_close"])
    assert (z == 4).sum() == sum(ser["expired"])
    assert res["review_recall"] + res["realised_miss_rate"] + res["expired_positive_rate"] + res[
        "open_backlog_positive_rate"
    ] == pytest.approx(1.0)


def test_daily_capacity_is_respected():
    day, s, y = make_stream(prev=0.05)
    res = simulate(day, s, y, r=0.03, policy=PolicyConfig("static", 0.1), cal_scores=cal())
    for n_new, rv in zip(res["series"]["n_new"], res["series"]["review"]):
        assert rv <= math.ceil(0.03 * n_new)


def test_no_autoclose_baseline():
    day, s, y = make_stream()
    res = simulate(day, s, y, r=0.05, policy=PolicyConfig("none"), cal_scores=cal())
    assert res["auto_closed_cases"] == 0 and res["workload_removed"] == 0.0


def test_tau_functions():
    x = np.arange(1.0, 10.0)  # n = 9
    assert conformal_tau(x, 0.1) == 1.0  # k = floor(0.1*10) = 1 -> smallest
    assert conformal_tau(np.arange(1.0, 9.0), 0.1) == float("-inf")  # n=8 -> k=0
    assert empirical_tau(x, 0.5) == 5.0
    assert empirical_tau(np.array([]), 0.1) == float("-inf")


def test_iid_realised_miss_matches_nominal_alpha():
    """Sanity: with exchangeable calibration/test positives, static tolerance ~ realised miss."""
    day, s, y = make_stream(n_days=60, per_day=400, prev=0.5)
    res = simulate(day, s, y, r=0.0, policy=PolicyConfig("static", 0.10), cal_scores=cal())
    assert abs(res["realised_miss_rate"] - 0.10) < 0.02


def test_engine_measures_failure_under_shift():
    """Positives in the stream score much lower than in calibration -> tolerance is badly violated."""
    day, s, y = make_stream(n_days=60, per_day=400, prev=0.5, pos_ab=(2, 5))
    res = simulate(day, s, y, r=0.0, policy=PolicyConfig("static", 0.10), cal_scores=cal(ab=(5, 2)))
    assert res["realised_miss_rate"] > 0.35 and res["violation_rate"] == 1.0


def test_backlog_expiry():
    day, s, y = make_stream(n_days=30, per_day=100, prev=0.5)
    res = simulate(day, s, y, r=0.0, policy=PolicyConfig("none", expiry=3), cal_scores=cal(), return_zone=True)
    assert res["expired_positive_rate"] > 0.85
    assert res["expired_positive_rate"] + res["open_backlog_positive_rate"] == pytest.approx(1.0)
    assert res["max_backlog"] <= 2 * 100 + 100


def test_rolling_equals_static_when_no_labels_arrive():
    day, s, y = make_stream(n_days=30)
    a = simulate(day, s, y, r=0.02, policy=PolicyConfig("static", 0.1), cal_scores=cal())
    b = simulate(day, s, y, r=0.02, policy=PolicyConfig("rolling", 0.1, label_delay=10_000), cal_scores=cal())
    assert a["auto_closed_cases"] == b["auto_closed_cases"]


def test_conformal_refuses_to_autoclose_without_enough_labels():
    day, s, y = make_stream(n_days=30)
    res = simulate(day, s, y, r=0.02, policy=PolicyConfig("conformal", 0.1, label_delay=10_000), cal_scores=cal(n=5))
    assert res["auto_closed_cases"] == 0


def test_rolling_adapts_to_shift_better_than_static():
    day, s, y = make_stream(n_days=90, per_day=300, prev=0.5, pos_ab=(2, 5))
    st = simulate(day, s, y, r=0.0, policy=PolicyConfig("static", 0.1), cal_scores=cal())
    ro = simulate(day, s, y, r=0.0, policy=PolicyConfig("rolling", 0.1), cal_scores=cal())
    assert ro["realised_miss_rate"] < st["realised_miss_rate"]


def test_review_only_label_regime_runs():
    day, s, y = make_stream(prev=0.1)
    res = simulate(day, s, y, r=0.05, policy=PolicyConfig("rolling", 0.1, label_regime="review_only"), cal_scores=cal())
    assert 0 <= res["realised_miss_rate"] <= 1
