"""numbeopy — data models.

Numbeo exposes seven kinds of public tables:
    - Country-level cost-of-living prices (country_result.jsp)                → list[Price]
    - City-level cost-of-living prices    (city_result.jsp)                   → list[Price]
    - City indices in the country page    (country_result.jsp Table 4)        → list[CityIndices]
    - Country-level cost-of-living index rankings (rankings_by_country.jsp)   → dict → CountryData.indices
    - Country-level Quality of Life composite      (quality_of_life/…)        → QoLIndices
    - Country-level Property / rental / mortgage   (property-investment/…)    → PropertyIndices
    - Country-level Crime / Health / Pollution / Traffic composites           → CrimeIndices etc.

`CountryData` composes these together. `CityData` is the city-level analogue for
prices only (the extended category indices remain country-level in Numbeo).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Price:
    """One item-price row from a country_result.jsp or city_result.jsp page."""
    category: str          # "Restaurants" | "Markets" | "Transportation" | ...
    item: str
    price: float
    range_low: float | None = None
    range_high: float | None = None
    currency: str = "USD"
    has_price: bool = True


@dataclass(frozen=True)
class CityIndices:
    """One row from the per-country city-indices table (country_result.jsp Table 4)."""
    city: str
    cost_of_living_index: float | None = None
    rent_index: float | None = None
    cost_of_living_plus_rent_index: float | None = None
    groceries_index: float | None = None
    restaurant_price_index: float | None = None
    local_purchasing_power_index: float | None = None


@dataclass(frozen=True)
class QoLIndices:
    """One row from quality-of-life/rankings_by_country.jsp."""
    country: str
    quality_of_life_index: float | None = None
    purchasing_power_index: float | None = None
    safety_index: float | None = None
    health_care_index: float | None = None
    cost_of_living_index: float | None = None
    property_price_to_income_ratio: float | None = None
    traffic_commute_time_index: float | None = None
    pollution_index: float | None = None
    climate_index: float | None = None
    extras: dict[str, float] = field(default_factory=dict)   # any additional columns Numbeo may add


@dataclass(frozen=True)
class PropertyIndices:
    """One row from property-investment/rankings_by_country.jsp or rankings.jsp (city)."""
    location: str                # country name (country page) or city name (city page)
    scope: str = "country"       # "country" | "city"
    price_to_income_ratio: float | None = None
    gross_rental_yield_city_centre: float | None = None
    gross_rental_yield_outside_centre: float | None = None
    price_to_rent_ratio_city_centre: float | None = None
    price_to_rent_ratio_outside_centre: float | None = None
    mortgage_as_percentage_of_income: float | None = None
    affordability_index: float | None = None
    extras: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class CrimeIndices:
    """One row from crime/rankings_by_country.jsp."""
    country: str
    crime_index: float | None = None
    safety_index: float | None = None


@dataclass(frozen=True)
class HealthCareIndices:
    """One row from health-care/rankings_by_country.jsp."""
    country: str
    health_care_index: float | None = None
    health_care_exp_index: float | None = None


@dataclass(frozen=True)
class PollutionIndices:
    """One row from pollution/rankings_by_country.jsp."""
    country: str
    pollution_index: float | None = None
    exp_pollution_index: float | None = None


@dataclass(frozen=True)
class TrafficIndices:
    """One row from traffic/rankings_by_country.jsp."""
    country: str
    traffic_index: float | None = None
    time_index_minutes: float | None = None
    time_exp_index: float | None = None
    inefficiency_index: float | None = None


@dataclass
class CountryData:
    """Full country snapshot from Numbeo.

    Populated by `Client.fetch_country()`. Categorical indices (QoL, property,
    crime, health, pollution, traffic) are populated only when
    `include_all_categories=True` is passed.
    """
    country: str
    currency: str
    prices: list[Price] = field(default_factory=list)
    cities: list[CityIndices] = field(default_factory=list)
    indices: dict[str, float] = field(default_factory=dict)        # cost-of-living country aggregate
    qol: QoLIndices | None = None
    property: PropertyIndices | None = None
    crime: CrimeIndices | None = None
    health_care: HealthCareIndices | None = None
    pollution: PollutionIndices | None = None
    traffic: TrafficIndices | None = None
    fetched_at: str = field(default_factory=_utcnow)
    source_url: str = ""
    source_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        def _as_dict(obj):
            if obj is None:
                return None
            return {k: v for k, v in obj.__dict__.items()}
        return {
            "country": self.country,
            "currency": self.currency,
            "fetched_at": self.fetched_at,
            "source_url": self.source_url,
            "source_sha256": self.source_sha256,
            "indices": self.indices,
            "prices": [
                {
                    "category": p.category, "item": p.item, "price": p.price,
                    "range_low": p.range_low, "range_high": p.range_high,
                    "currency": p.currency, "has_price": p.has_price,
                } for p in self.prices
            ],
            "cities": [_as_dict(c) for c in self.cities],
            "qol": _as_dict(self.qol),
            "property": _as_dict(self.property),
            "crime": _as_dict(self.crime),
            "health_care": _as_dict(self.health_care),
            "pollution": _as_dict(self.pollution),
            "traffic": _as_dict(self.traffic),
        }


@dataclass
class CityData:
    """One-city snapshot: cost-of-living prices for a specific city.

    Numbeo publishes the same 50+ item table on city_result.jsp as on
    country_result.jsp, but city-averaged instead of country-averaged. Category
    indices (QoL / crime / health / etc.) remain country-level in Numbeo.
    """
    country: str
    city: str
    currency: str
    prices: list[Price] = field(default_factory=list)
    fetched_at: str = field(default_factory=_utcnow)
    source_url: str = ""
    source_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "city": self.city,
            "currency": self.currency,
            "fetched_at": self.fetched_at,
            "source_url": self.source_url,
            "source_sha256": self.source_sha256,
            "prices": [
                {
                    "category": p.category, "item": p.item, "price": p.price,
                    "range_low": p.range_low, "range_high": p.range_high,
                    "currency": p.currency, "has_price": p.has_price,
                } for p in self.prices
            ],
        }
