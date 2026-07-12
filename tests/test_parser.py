"""Offline tests for numbeopy.parser using saved HTML fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from numbeopy.models import (
    CityIndices,
    CrimeIndices,
    HealthCareIndices,
    PollutionIndices,
    Price,
    PropertyIndices,
    QoLIndices,
    TrafficIndices,
)
from numbeopy.parser import (
    parse_city_page,
    parse_country_page,
    parse_country_rankings,
    parse_country_rankings_full,
    parse_crime_rankings,
    parse_health_care_rankings,
    parse_pollution_rankings,
    parse_property_rankings_by_city,
    parse_property_rankings_by_country,
    parse_qol_rankings,
    parse_traffic_rankings,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def turkey_html() -> str:
    return _read("country_result_turkey.html")


@pytest.fixture
def rankings_html() -> str:
    return _read("rankings_by_country_usd.html")


@pytest.fixture
def istanbul_html() -> str:
    return _read("city_result_istanbul.html")


@pytest.fixture
def qol_html() -> str:
    return _read("quality_of_life_rankings.html")


@pytest.fixture
def property_country_html() -> str:
    return _read("property_rankings_country.html")


@pytest.fixture
def property_city_html() -> str:
    return _read("property_rankings_city.html")


@pytest.fixture
def crime_html() -> str:
    return _read("crime_rankings.html")


@pytest.fixture
def health_html() -> str:
    return _read("health_care_rankings.html")


@pytest.fixture
def pollution_html() -> str:
    return _read("pollution_rankings.html")


@pytest.fixture
def traffic_html() -> str:
    return _read("traffic_rankings.html")


# ═══════════════════════════════════════════════════════════════════════
# country_result.jsp (existing v0.1.0 coverage)
# ═══════════════════════════════════════════════════════════════════════

class TestCountryPage:
    def test_parses_country_metadata(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey", currency="USD")
        assert data.country == "Turkey"
        assert data.currency == "USD"

    def test_extracts_many_prices(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        assert len(data.prices) >= 40

    def test_prices_have_expected_categories(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        cats = {p.category for p in data.prices}
        expected = {
            "Restaurants", "Markets", "Transportation",
            "Utilities (Monthly)", "Rent Per Month",
        }
        missing = expected - cats
        assert not missing, f"missing categories: {missing}"

    def test_all_prices_are_dataclass_and_normalized(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey", currency="USD")
        for p in data.prices:
            assert isinstance(p, Price)
            assert p.currency == "USD"

    def test_extracts_cities(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        assert len(data.cities) >= 3
        for c in data.cities:
            assert isinstance(c, CityIndices)

    def test_istanbul_present(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        cities = {c.city for c in data.cities}
        assert "Istanbul" in cities


class TestRankings:
    def test_list_countries_returns_many(self, rankings_html: str) -> None:
        countries = parse_country_rankings(rankings_html)
        assert len(countries) >= 100

    def test_rankings_full_dict_shape(self, rankings_html: str) -> None:
        full = parse_country_rankings_full(rankings_html)
        assert "Turkey" in full
        assert "Cost of Living Index" in full["Turkey"]


# ═══════════════════════════════════════════════════════════════════════
# v0.2.0 new: city_result.jsp
# ═══════════════════════════════════════════════════════════════════════

class TestCityPage:
    def test_parses_istanbul_prices(self, istanbul_html: str) -> None:
        data = parse_city_page(istanbul_html, country="Turkey", city="Istanbul")
        assert data.country == "Turkey"
        assert data.city == "Istanbul"
        assert len(data.prices) >= 40

    def test_prices_typed_as_dataclass(self, istanbul_html: str) -> None:
        data = parse_city_page(istanbul_html, country="Turkey", city="Istanbul")
        for p in data.prices:
            assert isinstance(p, Price)

    def test_istanbul_categories_include_rent(self, istanbul_html: str) -> None:
        data = parse_city_page(istanbul_html, country="Turkey", city="Istanbul")
        cats = {p.category for p in data.prices}
        assert "Rent Per Month" in cats


# ═══════════════════════════════════════════════════════════════════════
# v0.2.0 new: category rankings
# ═══════════════════════════════════════════════════════════════════════

class TestQoLRankings:
    def test_parses_many_countries(self, qol_html: str) -> None:
        result = parse_qol_rankings(qol_html)
        assert len(result) >= 50
        assert "Turkey" in result

    def test_turkey_row_is_qol_typed(self, qol_html: str) -> None:
        turkey = parse_qol_rankings(qol_html)["Turkey"]
        assert isinstance(turkey, QoLIndices)
        assert turkey.quality_of_life_index is not None
        assert turkey.quality_of_life_index > 0
        assert turkey.purchasing_power_index is not None


class TestPropertyRankings:
    def test_country_rankings_parses(self, property_country_html: str) -> None:
        result = parse_property_rankings_by_country(property_country_html)
        assert len(result) >= 50
        assert "Turkey" in result
        for p in result.values():
            assert isinstance(p, PropertyIndices)
            assert p.scope == "country"

    def test_city_rankings_parses(self, property_city_html: str) -> None:
        result = parse_property_rankings_by_city(property_city_html)
        assert len(result) >= 100     # global cities table has hundreds
        # every result should have city scope
        for p in result.values():
            assert isinstance(p, PropertyIndices)
            assert p.scope == "city"


class TestCrimeRankings:
    def test_parses_and_types(self, crime_html: str) -> None:
        result = parse_crime_rankings(crime_html)
        assert len(result) >= 50
        turkey = result.get("Turkey")
        assert turkey is not None
        assert isinstance(turkey, CrimeIndices)
        assert turkey.crime_index is not None
        assert turkey.safety_index is not None


class TestHealthCareRankings:
    def test_parses_and_types(self, health_html: str) -> None:
        result = parse_health_care_rankings(health_html)
        assert len(result) >= 30
        # Not all countries appear in every ranking; use any known one that likely appears
        assert "Turkey" in result or "United States" in result
        one = next(iter(result.values()))
        assert isinstance(one, HealthCareIndices)
        assert one.health_care_index is not None


class TestPollutionRankings:
    def test_parses_and_types(self, pollution_html: str) -> None:
        result = parse_pollution_rankings(pollution_html)
        assert len(result) >= 50
        turkey = result.get("Turkey")
        assert turkey is not None
        assert isinstance(turkey, PollutionIndices)
        assert turkey.pollution_index is not None


class TestTrafficRankings:
    def test_parses_and_types(self, traffic_html: str) -> None:
        result = parse_traffic_rankings(traffic_html)
        assert len(result) >= 30
        one = next(iter(result.values()))
        assert isinstance(one, TrafficIndices)
        assert one.traffic_index is not None
