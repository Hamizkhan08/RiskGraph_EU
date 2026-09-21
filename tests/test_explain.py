import numpy as np
import pandas as pd
import pytest

from riskgraph.explain import REASON_LABELS, case_evidence, contributions, explain_rows, reason_code
from riskgraph.features import FEATURES, build_cases
from riskgraph.models import ScoreModel


@pytest.fixture(scope="module")
def trained(fixture_td):
    ct = build_cases(fixture_td)
    cols = list(ct.X.columns)
    m = ScoreModel("lgbm", cols, seed=1).fit(ct.X, ct.y, neg_fraction=0.3)
    return fixture_td, ct, m


def test_treeshap_contributions_sum_to_margin(trained):
    _, ct, m = trained
    X = ct.X.iloc[:200]
    C, base = contributions(m, X)
    raw = m.est.booster_.predict(X[m.cols].to_numpy(), raw_score=True)
    assert np.allclose(C.sum(1) + base, raw, atol=1e-6)


def test_logistic_attribution_sums_to_decision_function(trained):
    _, ct, _ = trained
    lr = ScoreModel("logreg", list(ct.X.columns), seed=1).fit(ct.X, ct.y, neg_fraction=0.3)
    X = ct.X.iloc[:200]
    C, base = contributions(lr, X)
    z = lr.est.decision_function(X[lr.cols].to_numpy())
    assert np.allclose(C.sum(1) + base, z, atol=1e-6)


def test_every_feature_has_a_reason_code():
    for f in FEATURES:
        assert reason_code(f) in REASON_LABELS


def test_explain_rows_structure(trained):
    _, ct, m = trained
    e = explain_rows(m, ct.X.iloc[:3], top=5)
    assert len(e) == 3 and len(e[0]["top_features"]) == 5
    f = e[0]["top_features"][0]
    assert set(f) >= {"feature", "value", "contribution", "group", "definition", "reason_code"}
    assert abs(e[0]["margin"] - (e[0]["base_value"] + sum(c for c in contributions(m, ct.X.iloc[:1])[0][0]))) < 1e-6


def test_evidence_never_contains_future_transactions(trained):
    td, ct, _ = trained
    idx = np.flatnonzero(ct.y == 1)[:40]
    for i in idx:
        ev = case_evidence(td, int(ct.acct[i]), int(ct.day[i]))
        limit = pd.Timestamp(ev["decision_timestamp"])
        assert all(pd.Timestamp(t["timestamp"]) < limit for t in ev["transactions"])
        assert all(pd.Timestamp(e["last"]) < limit for e in ev["edges"])
        ids = {n["id"] for n in ev["nodes"]}
        assert ev["focal"] in ids and all(e["source"] in ids and e["target"] in ids for e in ev["edges"])
        assert len(ev["transactions"]) <= 15 and len(ev["nodes"]) <= 24
