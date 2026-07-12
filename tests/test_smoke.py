"""Live smoke test — hits Numbeo. Skipped if the network is unavailable.

Run explicitly with:
    pytest tests/test_smoke.py -v --run-live

Requires network; not part of the offline CI-friendly suite.
"""
from __future__ import annotations

import os
import socket

import pytest

from numbeopy import fetch_country, list_countries


def _network_available() -> bool:
    try:
        socket.create_connection(("www.numbeo.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


def _live_enabled() -> bool:
    return os.environ.get("NUMBEOPY_LIVE") == "1"


pytestmark = pytest.mark.skipif(
    not (_live_enabled() and _network_available()),
    reason="live network tests require NUMBEOPY_LIVE=1 and reachable Numbeo",
)


def test_list_countries_returns_many() -> None:
    countries = list_countries()
    assert len(countries) >= 100
    assert "Turkey" in countries


def test_fetch_turkey_full_snapshot() -> None:
    data = fetch_country("Turkey")
    assert len(data.prices) >= 40
    assert len(data.cities) >= 3
    assert data.indices.get("Cost of Living Index", 0) > 0
    assert data.source_url.startswith("https://www.numbeo.com/")
    assert len(data.source_sha256) == 64
