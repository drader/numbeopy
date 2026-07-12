"""numbeopy — Python client for Numbeo's public cost-of-living pages.

Public API:
    list_countries()                       → list[str]
    fetch_country(country, ...)            → CountryData    (cost-of-living page)
    fetch_country_prices(country, ...)     → list[Price]
    fetch_country_indices(country, ...)    → dict[str,float]
    fetch_city(country, city, ...)         → CityData
    quality_of_life_rankings()             → dict[country, QoLIndices]
    property_rankings_by_country()         → dict[country, PropertyIndices]
    property_rankings_by_city()            → dict[city, PropertyIndices]
    crime_rankings()                       → dict[country, CrimeIndices]
    health_care_rankings()                 → dict[country, HealthCareIndices]
    pollution_rankings()                   → dict[country, PollutionIndices]
    traffic_rankings()                     → dict[country, TrafficIndices]

All fetches are rate-limited (default 3s) and honour a polite User-Agent.
"""
from numbeopy.client import Client, DEFAULT_RATE_LIMIT_SECONDS, DEFAULT_USER_AGENT
from numbeopy.models import (
    CityData,
    CityIndices,
    CountryData,
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

__version__ = "0.2.0"

_default_client: Client | None = None


def _default() -> Client:
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def list_countries(currency: str = "USD") -> list[str]:
    return _default().list_countries(currency=currency)


def fetch_country(country: str, currency: str = "USD",
                  include_all_categories: bool = False) -> CountryData:
    return _default().fetch_country(country=country, currency=currency,
                                    include_all_categories=include_all_categories)


def fetch_country_prices(country: str, currency: str = "USD") -> list[Price]:
    return _default().fetch_country(country=country, currency=currency).prices


def fetch_country_indices(country: str, currency: str = "USD") -> dict[str, float]:
    return _default().fetch_country(country=country, currency=currency).indices


def fetch_city(country: str, city: str, currency: str = "USD") -> CityData:
    return _default().fetch_city(country=country, city=city, currency=currency)


def quality_of_life_rankings() -> dict[str, QoLIndices]:
    return _default().quality_of_life_rankings()


def property_rankings_by_country() -> dict[str, PropertyIndices]:
    return _default().property_rankings_by_country()


def property_rankings_by_city() -> dict[str, PropertyIndices]:
    return _default().property_rankings_by_city()


def crime_rankings() -> dict[str, CrimeIndices]:
    return _default().crime_rankings()


def health_care_rankings() -> dict[str, HealthCareIndices]:
    return _default().health_care_rankings()


def pollution_rankings() -> dict[str, PollutionIndices]:
    return _default().pollution_rankings()


def traffic_rankings() -> dict[str, TrafficIndices]:
    return _default().traffic_rankings()


__all__ = [
    "Client", "DEFAULT_RATE_LIMIT_SECONDS", "DEFAULT_USER_AGENT",
    "Price", "CityIndices", "CountryData", "CityData",
    "QoLIndices", "PropertyIndices",
    "CrimeIndices", "HealthCareIndices", "PollutionIndices", "TrafficIndices",
    "list_countries", "fetch_country", "fetch_country_prices",
    "fetch_country_indices", "fetch_city",
    "quality_of_life_rankings",
    "property_rankings_by_country", "property_rankings_by_city",
    "crime_rankings", "health_care_rankings",
    "pollution_rankings", "traffic_rankings",
    "parse_country_page", "parse_city_page",
    "parse_country_rankings", "parse_country_rankings_full",
    "parse_qol_rankings",
    "parse_property_rankings_by_country", "parse_property_rankings_by_city",
    "parse_crime_rankings", "parse_health_care_rankings",
    "parse_pollution_rankings", "parse_traffic_rankings",
    "__version__",
]
