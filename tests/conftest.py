"""Shared helpers: hand-built TxData for exact-value tests and a cached synthetic fixture."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from riskgraph.data.fixture import make_fixture  # noqa: E402
from riskgraph.data.schema import TxData  # noqa: E402


@pytest.fixture(scope="session")
def fixture_td() -> TxData:
    return make_fixture()
