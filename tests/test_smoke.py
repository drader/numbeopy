"""Live smoke tests — hit Numbeo. Gated on NUMBEOPY_LIVE=1.

Run explicitly:
    NUMBEOPY_LIVE=1 pytest tests/test_smoke.py -v
"""
from __future__ import annotations

import os
import socket

import pytest

from numbeopy import (
    Client,
    crime_rankings,
    fetch_city,
    fetch_country,
    health_care_rankings,
    list_countries,
    pollution_rankings,
    property_rankings_by_country,
    quality_of_life_rankings,
    traffic_rankings,
)


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


def test_fetch_turkey_all_categories() -> None:
    data = fetch_country("Turkey", include_all_categories=True)
    assert data.qol is not None and data.qol.quality_of_life_index is not None
    assert data.property is not None and data.property.price_to_income_ratio is not None
    assert data.crime is not None and data.crime.crime_index is not None
    assert data.health_care is not None and data.health_care.health_care_index is not None
    assert data.pollution is not None and data.pollution.pollution_index is not None
    assert data.traffic is not None and data.traffic.traffic_index is not None


def test_fetch_istanbul_city() -> None:
    data = fetch_city("Turkey", "Istanbul")
    assert data.city == "Istanbul"
    assert data.country == "Turkey"
    assert len(data.prices) >= 40


def test_quality_of_life_rankings() -> None:
    result = quality_of_life_rankings()
    assert len(result) >= 50
    assert "Turkey" in result
    assert result["Turkey"].quality_of_life_index is not None


def test_property_rankings_by_country() -> None:
    result = property_rankings_by_country()
    assert len(result) >= 50
    assert "Turkey" in result


def test_crime_rankings() -> None:
    result = crime_rankings()
    assert "Turkey" in result
    assert result["Turkey"].crime_index is not None


def test_health_care_rankings() -> None:
    result = health_care_rankings()
    assert len(result) >= 30


def test_pollution_rankings() -> None:
    result = pollution_rankings()
    assert "Turkey" in result


def test_traffic_rankings() -> None:
    result = traffic_rankings()
    assert len(result) >= 30


# Cache-behavior test lives in tests/test_client.py (offline, mocked session)
# so it doesn't consume Numbeo request budget or fail on 429.
