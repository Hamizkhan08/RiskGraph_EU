import numpy as np
import pytest

from riskgraph import experiments as E


@pytest.fixture(scope="module")
def stages(fixture_td):
    prep = E.prepare(fixture_td)
    h1, scores, _ = E.stage_h1(prep, seeds=(1,))
    h2, held = E.stage_h2(prep, scores, seeds=(1,))
    h3 = E.stage_h3(prep, scores, held, seeds=(1,))
    return prep, h1, scores, h2, h3


def test_h1_shapes_and_contrasts(stages):
    prep, h1, scores, _, _ = stages
    assert set(h1["models"]) == set(E.MODELS)
    assert all(np.isfinite(v).all() for v in scores.values())
    assert any(c["primary"] for c in h1["contrasts"])
    assert set(h1["calibration"]) == set(E.MODELS) and h1["counts"]["train_pos"] > 0
    for m in h1["models"].values():
        assert set(m["test"]) == {"strict", "all"} and "1.0" in m["test"]["strict"]["topk"]


def test_h2_covers_every_present_family(stages):
    prep, _, _, h2, _ = stages
    assert set(h2["families"]) == {"0", "1", "2"}
    for f in h2["families"].values():
        assert f["n_train_cases_removed"] > 0 and "M4_lgbm_TBGM" in f["by_m"]["1.0"]


def test_h3_grid_complete(stages):
    _, _, _, _, h3 = stages
    assert len(h3["same_regime"]) == 4 * 3 * 3  # m x policy x alpha
    assert len(h3["heldout"]) == 3 * 3 * 3  # family x policy x alpha
    assert {c["policy"]["kind"] for c in h3["same_regime"]} == {"static", "rolling", "conformal"}
    assert len(h3["review_only_labels"]) == 2 and set(h3["baseline_no_autoclose"]) == {"0.5", "1.0", "2.0", "5.0"}


def test_primary_simulation_zones(stages):
    prep, _, scores, _, _ = stages
    res = E.primary_simulation(prep, scores, 1)
    assert set(np.unique(res["zone"])) <= {1, 2, 3, 4}
