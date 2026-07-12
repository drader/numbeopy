"""numbeopy — Python client for Numbeo's public cost-of-living pages.

Public API:
    list_countries()             → list[str]     rankings_by_country page
    fetch_country(country, ...)  → CountryData   country_result page
    fetch_country_prices(...)    → list[Price]   just the item prices
    fetch_country_indices(...)   → dict[str,float] just the aggregate indices

All fetches are rate-limited (default 3.0s between requests) and honour a
polite User-Agent. Data pages are HTML tables consumed via pandas.read_html.
"""
from numbeopy.client import Client, DEFAULT_RATE_LIMIT_SECONDS, DEFAULT_USER_AGENT
from numbeopy.models import CountryData, Price
from numbeopy.parser import parse_country_page, parse_country_rankings

__version__ = "0.1.0"

_default_client: Client | None = None


def _default() -> Client:
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def list_countries(currency: str = "USD") -> list[str]:
    """Return the list of country names Numbeo publishes on its rankings page."""
    return _default().list_countries(currency=currency)


def fetch_country(country: str, currency: str = "USD") -> CountryData:
    """Fetch full CountryData (prices + indices) for one country name."""
    return _default().fetch_country(country=country, currency=currency)


def fetch_country_prices(country: str, currency: str = "USD") -> list[Price]:
    """Fetch just the item-level prices for one country name."""
    return _default().fetch_country(country=country, currency=currency).prices


def fetch_country_indices(country: str, currency: str = "USD") -> dict[str, float]:
    """Fetch just the aggregate quality-of-life / cost-of-living indices."""
    return _default().fetch_country(country=country, currency=currency).indices


__all__ = [
    "Client",
    "CountryData",
    "Price",
    "DEFAULT_RATE_LIMIT_SECONDS",
    "DEFAULT_USER_AGENT",
    "list_countries",
    "fetch_country",
    "fetch_country_prices",
    "fetch_country_indices",
    "parse_country_page",
    "parse_country_rankings",
    "__version__",
]
