import numpy as np
import pytest
from helpers_core import make_txdata

from riskgraph.features import FEATURES, GROUPS, build_cases, feature_names
from riskgraph.leakage import forbidden_feature_names


def _row(ct, acct, day):
    m = (ct.acct == acct) & (ct.day == day)
    assert m.sum() == 1, f"expected exactly one case for ({acct},{day})"
    return ct.X[m].iloc[0]


def test_registry_is_complete_and_clean():
    assert set(FEATURES) == set(feature_names())
    assert {g for g, _ in FEATURES.values()} == set(GROUPS)
    assert all(d for _, d in FEATURES.values()), "every feature needs a definition"
    assert forbidden_feature_names(list(FEATURES)) == []


def test_exact_values_small_graph():
    rows = [
        (3, 10, "A", "B", 100.0, "transfer", "EUR", 0),
        (3, 11, "A", "C", 50.0, "payment", "GBP", 0),
        (4, 9, "B", "A", 30.0, "transfer", "EUR", 0),
    ]
    ct = build_cases(make_txdata(rows), burn_in=0)
    assert len(ct.y) == 5  # (A,3) (B,3) (C,3) (A,4) (B,4)
    a3 = _row(ct, 0, 3)
    assert a3.t_n_out_1d == 2 and a3.t_n_in_1d == 0
    assert a3.t_amt_out_1d == 150 and a3.t_max_out_1d == 100 and a3.t_mean_out_1d == 75
    assert a3.t_n_transfer_out_1d == 1 and a3.t_n_payment_1d == 1
    assert a3.b_new_cp_out_1d == 2 and a3.b_distinct_cp_30d == 2 and a3.t_n_ccy_7d == 2
    assert a3.b_recip_cp_cum == 0
    assert a3.t_out_in_ratio_1d == pytest.approx(np.log1p(150.0))
    a4 = _row(ct, 0, 4)
    assert a4.t_n_in_1d == 1 and a4.t_n_out_7d == 2 and a4.t_amt_in_7d == 30
    assert a4.b_new_cp_in_1d == 1  # directed pair B->A first seen on day 4
    assert a4.b_recip_cp_cum == 1  # A<->B reciprocal from day 4
    assert _row(ct, 1, 4).b_recip_cp_cum == 1


def test_window_boundaries_are_trailing_and_inclusive():
    rows = [
        (0, 1, "A", "B", 1.0, "payment", "EUR", 0),
        (6, 1, "A", "C", 1.0, "payment", "EUR", 0),
        (7, 1, "A", "D", 1.0, "payment", "EUR", 0),
    ]
    ct = build_cases(make_txdata(rows), burn_in=0)
    assert _row(ct, 0, 6).t_n_out_7d == 2  # days 0..6 -> includes day 0
    assert _row(ct, 0, 7).t_n_out_7d == 2  # days 1..7 -> day 0 dropped
    assert _row(ct, 0, 7).t_n_out_30d == 3


def test_three_cycle_and_degree_features():
    rows = [
        (5, 1, "A", "B", 10.0, "transfer", "EUR", 0),
        (5, 2, "B", "C", 10.0, "transfer", "EUR", 0),
        (5, 3, "C", "A", 10.0, "transfer", "EUR", 0),
    ]
    ct = build_cases(make_txdata(rows), burn_in=0)
    a = _row(ct, 0, 5)
    assert a.m_cycle3_7d == 1 and a.g_deg_und_7d == 2 and a.g_reach2_7d == 2
    assert a.g_triangles_7d == 1 and a.m_cycle2_7d == 0


def test_near_threshold_feature():
    rows = [
        (2, 1, "A", "B", 9500.0, "deposit", "EUR", 0),
        (2, 2, "A", "C", 9000.0, "deposit", "EUR", 0),
        (2, 3, "A", "D", 8999.0, "deposit", "EUR", 0),
    ]
    ct = build_cases(make_txdata(rows), burn_in=0)
    assert _row(ct, 0, 2).m_near10k_1d == 2


def test_burn_in_days_are_not_cases_and_no_nan(fixture_td):
    ct = build_cases(fixture_td, burn_in=30)
    assert ct.day.min() >= 30
    X = ct.X.to_numpy()
    assert np.isfinite(X).all()


def test_labels_never_in_feature_matrix(fixture_td):
    ct = build_cases(fixture_td)
    assert list(ct.X.columns) == list(FEATURES)


def test_case_cache_roundtrip_is_pickle_free(fixture_td, tmp_path):
    from riskgraph.features import load_cases, save_cases

    ct = build_cases(fixture_td)
    save_cases(ct, tmp_path / "c.npz")
    back = load_cases(tmp_path / "c.npz")
    assert list(back.X.columns) == list(ct.X.columns)
    assert np.array_equal(back.X.to_numpy(), ct.X.to_numpy())
    for f in ("acct", "day", "y", "scheme_min_start", "scheme_max_start", "family_mask", "scheme_first"):
        assert np.array_equal(getattr(back, f), getattr(ct, f))
    assert back.feature_version == ct.feature_version
