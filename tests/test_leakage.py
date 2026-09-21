import numpy as np
import pandas as pd

from riskgraph.features import build_cases
from riskgraph.leakage import (
    forbidden_feature_names,
    future_perturbation_check,
    label_independence_check,
    split_integrity,
)
from riskgraph.models import PlattCalibrator, ScoreModel
from riskgraph.split import carry_over, eval_mask, make_split


def test_future_perturbation_passes(fixture_td):
    r = future_perturbation_check(fixture_td, 60)
    assert r["ok"] and r["max_abs_diff"] < 1e-6 and r["cases_compared"] > 1000


def test_future_perturbation_catches_a_leaky_builder(fixture_td):
    """Mutation test: a builder that peeks one day ahead MUST be flagged."""

    def leaky(td, max_day=None, burn_in=30):
        ct = build_cases(td, burn_in=burn_in, max_day=max_day)
        tx = td.tx if max_day is None else td.tx[td.tx["day"] <= max_day]
        tx = tx[tx["in_period"] & (tx["src_idx"] >= 0)]
        nxt = tx.groupby(["src_idx", "day"]).size()
        key = pd.MultiIndex.from_arrays([ct.acct, ct.day + 1])
        ct.X["t_n_out_1d"] = nxt.reindex(key).fillna(0).to_numpy().astype("float32")
        return ct

    assert future_perturbation_check(fixture_td, 60, builder=leaky)["ok"] is False


def test_label_independence_passes_and_catches_label_use(fixture_td):
    assert label_independence_check(fixture_td)["ok"]

    def uses_labels(td, max_day=None):
        ct = build_cases(td)
        ct.X["t_n_out_1d"] = ct.X["t_n_out_1d"] + ct.y.astype("float32")
        return ct

    assert label_independence_check(fixture_td, builder=uses_labels)["ok"] is False


def test_forbidden_names_detector():
    assert forbidden_feature_names(["t_n_out_1d", "is_fraud_flag", "scheme_id_x", "family_bit"]) == [
        "is_fraud_flag",
        "scheme_id_x",
        "family_bit",
    ]


def test_split_integrity_and_carry_over(fixture_td):
    ct = build_cases(fixture_td)
    sp = make_split(fixture_td.n_days)
    assert split_integrity(ct, sp)["ok"]
    co = carry_over(ct, sp.test[0])
    assert co.sum() > 0, "fixture schemes starting before the test block should exist"
    strict = eval_mask(ct, sp, "test", "strict")
    assert not (strict & co).any()
    assert eval_mask(ct, sp, "test", "all").sum() >= strict.sum()


def test_scaler_sees_only_training_rows(fixture_td):
    ct = build_cases(fixture_td)
    sp = make_split(fixture_td.n_days)
    tr = np.flatnonzero((ct.day >= sp.train[0]) & (ct.day < sp.train[1]))
    m = ScoreModel("logreg", list(ct.X.columns), seed=0).fit(ct.X.iloc[tr], ct.y[tr])
    assert m.est.named_steps["scale"].n_samples_seen_ == m.n_train_rows <= len(tr)


def test_platt_calibrator_is_monotone():
    rng = np.random.default_rng(0)
    s = rng.random(5000)
    y = (rng.random(5000) < s**2).astype(int)
    cal = PlattCalibrator().fit(s, y)
    grid = np.linspace(0.01, 0.99, 50)
    assert (np.diff(cal.transform(grid)) >= 0).all()
