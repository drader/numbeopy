"""Offline tests for numbeopy.parser using saved HTML fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from numbeopy.models import CityIndices, Price
from numbeopy.parser import (
    parse_country_page,
    parse_country_rankings,
    parse_country_rankings_full,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def turkey_html() -> str:
    return (FIXTURES / "country_result_turkey.html").read_text(encoding="utf-8")


@pytest.fixture
def rankings_html() -> str:
    return (FIXTURES / "rankings_by_country_usd.html").read_text(encoding="utf-8")


class TestCountryPage:
    def test_parses_country_metadata(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey", currency="USD")
        assert data.country == "Turkey"
        assert data.currency == "USD"

    def test_extracts_many_prices(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        # Numbeo publishes 50+ item prices per country page.
        assert len(data.prices) >= 40, f"expected 40+ prices, got {len(data.prices)}"

    def test_prices_have_expected_categories(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        cats = {p.category for p in data.prices}
        expected = {
            "Restaurants", "Markets", "Transportation",
            "Utilities (Monthly)", "Rent Per Month",
        }
        missing = expected - cats
        assert not missing, f"missing categories: {missing}; got {cats}"

    def test_all_prices_are_dataclass_and_normalized(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey", currency="USD")
        for p in data.prices:
            assert isinstance(p, Price)
            assert p.currency == "USD"
            assert isinstance(p.price, float)

    def test_at_least_some_prices_populated(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        populated = [p for p in data.prices if p.has_price and p.price > 0]
        assert len(populated) >= 30, "expected most prices to be populated for Turkey"

    def test_extracts_cities(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        assert len(data.cities) >= 3, f"expected 3+ Turkish cities, got {len(data.cities)}"
        for c in data.cities:
            assert isinstance(c, CityIndices)
            assert c.city and c.city.lower() != "nan"

    def test_istanbul_present(self, turkey_html: str) -> None:
        data = parse_country_page(turkey_html, country="Turkey")
        cities = {c.city for c in data.cities}
        assert "Istanbul" in cities, f"Istanbul should appear; got {cities}"


class TestRankings:
    def test_list_countries_returns_many(self, rankings_html: str) -> None:
        countries = parse_country_rankings(rankings_html)
        assert len(countries) >= 100, f"expected 100+ countries, got {len(countries)}"

    def test_rankings_full_dict_shape(self, rankings_html: str) -> None:
        full = parse_country_rankings_full(rankings_html)
        assert "Turkey" in full, "Turkey should appear in rankings"
        turkey_indices = full["Turkey"]
        assert "Cost of Living Index" in turkey_indices
        assert "Local Purchasing Power Index" in turkey_indices
        assert isinstance(turkey_indices["Cost of Living Index"], float)

    def test_rankings_values_are_numeric(self, rankings_html: str) -> None:
        full = parse_country_rankings_full(rankings_html)
        for country, indices in full.items():
            for name, value in indices.items():
                assert isinstance(value, float), f"{country}.{name} not float"
                assert value > 0, f"{country}.{name} is {value}"
