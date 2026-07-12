"""numbeopy — data models.

Numbeo publishes three kinds of tables:
    - Country-level item prices  (73 rows on country_result.jsp)     → list[Price]
    - City-level aggregate indices (~8 rows on country_result.jsp)   → list[CityIndices]
    - Country-level aggregate indices (~152 rows on rankings page)   → CountryData.indices dict

All three are folded into `CountryData` when `Client.fetch_country()` is called
with `include_country_indices=True` (the default), because a complete country
snapshot is usually what a caller wants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Price:
    """One item-price row from a country_result.jsp page (Table 1)."""
    category: str          # "Restaurants" | "Markets" | "Transportation" | ...
    item: str              # "Meal, Inexpensive Restaurant"
    price: float           # numeric value in `currency`
    range_low: float | None = None
    range_high: float | None = None
    currency: str = "USD"
    has_price: bool = True     # False when source cell was empty / "?"


@dataclass(frozen=True)
class CityIndices:
    """One row from the per-country city-indices table (Table 4)."""
    city: str
    cost_of_living_index: float | None = None
    rent_index: float | None = None
    cost_of_living_plus_rent_index: float | None = None
    groceries_index: float | None = None
    restaurant_price_index: float | None = None
    local_purchasing_power_index: float | None = None


@dataclass
class CountryData:
    """Snapshot of one country from Numbeo.

    Populated from country_result.jsp (prices + cities) and optionally
    augmented with country-level aggregate indices from rankings_by_country.jsp.
    """
    country: str
    currency: str
    prices: list[Price] = field(default_factory=list)
    cities: list[CityIndices] = field(default_factory=list)
    indices: dict[str, float] = field(default_factory=dict)   # country-level aggregates
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    source_url: str = ""
    source_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "currency": self.currency,
            "fetched_at": self.fetched_at,
            "source_url": self.source_url,
            "source_sha256": self.source_sha256,
            "indices": self.indices,
            "prices": [
                {
                    "category": p.category,
                    "item": p.item,
                    "price": p.price,
                    "range_low": p.range_low,
                    "range_high": p.range_high,
                    "currency": p.currency,
                    "has_price": p.has_price,
                }
                for p in self.prices
            ],
            "cities": [
                {
                    "city": c.city,
                    "cost_of_living_index": c.cost_of_living_index,
                    "rent_index": c.rent_index,
                    "cost_of_living_plus_rent_index": c.cost_of_living_plus_rent_index,
                    "groceries_index": c.groceries_index,
                    "restaurant_price_index": c.restaurant_price_index,
                    "local_purchasing_power_index": c.local_purchasing_power_index,
                }
                for c in self.cities
            ],
        }
