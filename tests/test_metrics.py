import numpy as np
import pytest

from riskgraph.metrics import calibration_bins, cluster_bootstrap_recall, daily_topk_mask, ece, pr_auc, topk_summary


def test_daily_topk_mask_exact():
    day = np.array([0, 0, 0, 0, 1, 1])
    score = np.array([0.9, 0.1, 0.8, 0.2, 0.5, 0.4])
    assert daily_topk_mask(day, score, 0.5).tolist() == [True, False, True, False, True, False]


def test_topk_summary_exact():
    day = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    score = np.array([0.9, 0.8, 0.1, 0.2, 0.9, 0.1, 0.2, 0.3])
    y = np.array([1, 0, 0, 1, 1, 0, 0, 0])
    s = topk_summary(day, score, y, 0.25)  # K = 1 per day
    assert s["n_review"] == 2 and s["tp"] == 2 and s["recall"] == pytest.approx(2 / 3)
    assert s["precision"] == 1.0 and s["lift"] == pytest.approx(1.0 / (3 / 8))


def test_pr_auc_perfect_and_nan_without_positives():
    assert pr_auc(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert np.isnan(pr_auc(np.zeros(4, dtype=int), np.arange(4.0)))


def test_ece_small_for_calibrated_predictions():
    rng = np.random.default_rng(1)
    p = rng.random(60000)
    y = (rng.random(60000) < p).astype(int)
    assert ece(y, p) < 0.02
    assert sum(b["n"] for b in calibration_bins(y, p)) == 60000


def test_cluster_bootstrap_paired():
    cluster = np.array([0, 0, 1, 1, 2, 2, -1, -1])
    y = np.array([1, 1, 1, 1, 1, 1, 0, 0])
    a = np.array([1, 1, 1, 1, 0, 0, 0, 0], dtype=bool)
    b = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=bool)
    r = cluster_bootstrap_recall(cluster, y, a, b, n_boot=400, seed=0)
    assert r["recall"] == pytest.approx(4 / 6) and r["recall_b"] == pytest.approx(1 / 6)
    assert r["diff"] > 0 and r["n_clusters"] == 3
    assert r["ci95"][0] <= r["recall"] <= r["ci95"][1]
