import pytest

from riskgraph.split import make_split


def test_blocks_ordered_and_cover():
    sp = make_split(365)
    assert sp.burn_in == 30
    assert sp.train[0] == 30 and sp.train[1] == sp.val[0]
    assert sp.val[1] == sp.purge[0] and sp.purge[1] == sp.test[0] and sp.test[1] == 365
    assert sp.purge[1] - sp.purge[0] == 14


def test_degenerate_split_raises():
    with pytest.raises(ValueError):
        make_split(40)
