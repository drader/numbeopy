"""numbeopy — HTTP client with rate limiting.

The `Client` class fetches Numbeo public HTML pages and hands them to
`numbeopy.parser`. All requests share a per-instance rate limiter (default
3s between requests) and a polite User-Agent identifying the client.

Public endpoints supported (v0.2.0):
    /cost-of-living/country_result.jsp?country=<X>       — country prices + city indices
    /cost-of-living/city_result.jsp?country=<X>&city=<Y> — city prices
    /cost-of-living/rankings_by_country.jsp              — country COL aggregate indices
    /quality-of-life/rankings_by_country.jsp             — Quality of Life composite
    /property-investment/rankings_by_country.jsp         — Property (country)
    /property-investment/rankings.jsp                    — Property (city)
    /crime/rankings_by_country.jsp                       — Crime + Safety
    /health-care/rankings_by_country.jsp                 — Health Care
    /pollution/rankings_by_country.jsp                   — Pollution
    /traffic/rankings_by_country.jsp                     — Traffic

Not supported (by design — see README rationale):
    bulk fetch of all 12,790 city_result pages
"""
from __future__ import annotations

import hashlib
import time
from urllib.parse import quote_plus

import requests

from numbeopy.models import (
    CityData,
    CountryData,
    CrimeIndices,
    HealthCareIndices,
    PollutionIndices,
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

DEFAULT_RATE_LIMIT_SECONDS: float = 3.0
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_USER_AGENT: str = "numbeopy/0.2 (+https://github.com/drader/numbeopy)"

BASE = "https://www.numbeo.com"


class Client:
    """Rate-limited HTTP client for Numbeo public cost-of-living pages."""

    def __init__(
        self,
        *,
        rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        session: requests.Session | None = None,
    ) -> None:
        self.rate_limit_seconds = float(rate_limit_seconds)
        self.timeout_seconds = float(timeout_seconds)
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", user_agent)
        self._last_call: float = 0.0
        self._rankings_cache: dict[str, dict[str, dict[str, float]]] = {}
        self._qol_cache: dict[str, QoLIndices] | None = None
        self._property_country_cache: dict[str, PropertyIndices] | None = None
        self._property_city_cache: dict[str, PropertyIndices] | None = None
        self._crime_cache: dict[str, CrimeIndices] | None = None
        self._health_care_cache: dict[str, HealthCareIndices] | None = None
        self._pollution_cache: dict[str, PollutionIndices] | None = None
        self._traffic_cache: dict[str, TrafficIndices] | None = None

    # ─── low-level ───

    def _sleep_if_needed(self) -> None:
        now = time.monotonic()
        delay = self._last_call + self.rate_limit_seconds - now
        if delay > 0:
            time.sleep(delay)
        self._last_call = time.monotonic()

    def _get_html(self, url: str) -> tuple[str, str]:
        self._sleep_if_needed()
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.text, hashlib.sha256(response.content).hexdigest()

    # ─── cost-of-living rankings (existing) ───

    def _rankings_full(self, currency: str) -> dict[str, dict[str, float]]:
        if currency not in self._rankings_cache:
            url = f"{BASE}/cost-of-living/rankings_by_country.jsp?displayCurrency={currency}"
            html, _ = self._get_html(url)
            self._rankings_cache[currency] = parse_country_rankings_full(html)
        return self._rankings_cache[currency]

    def list_countries(self, *, currency: str = "USD") -> list[str]:
        return list(self._rankings_full(currency=currency).keys())

    def country_indices(self, country: str, *, currency: str = "USD") -> dict[str, float]:
        return dict(self._rankings_full(currency=currency).get(country, {}))

    # ─── country + city snapshots (existing + new) ───

    def fetch_country(
        self,
        *,
        country: str,
        currency: str = "USD",
        include_country_indices: bool = True,
        include_all_categories: bool = False,
    ) -> CountryData:
        encoded = quote_plus(country)
        url = f"{BASE}/cost-of-living/country_result.jsp?country={encoded}&displayCurrency={currency}"
        html, sha = self._get_html(url)
        data = parse_country_page(html, country=country, currency=currency)
        data.source_url = url
        data.source_sha256 = sha
        if include_country_indices:
            data.indices = self.country_indices(country, currency=currency)
        if include_all_categories:
            # These populate/reuse per-category caches; each is one HTTP call.
            data.qol = self.quality_of_life_rankings().get(country)
            data.property = self.property_rankings_by_country().get(country)
            data.crime = self.crime_rankings().get(country)
            data.health_care = self.health_care_rankings().get(country)
            data.pollution = self.pollution_rankings().get(country)
            data.traffic = self.traffic_rankings().get(country)
        return data

    def fetch_city(self, *, country: str, city: str, currency: str = "USD") -> CityData:
        country_enc = quote_plus(country)
        city_enc = quote_plus(city)
        url = f"{BASE}/cost-of-living/city_result.jsp?country={country_enc}&city={city_enc}&displayCurrency={currency}"
        html, sha = self._get_html(url)
        data = parse_city_page(html, country=country, city=city, currency=currency)
        data.source_url = url
        data.source_sha256 = sha
        return data

    # ─── category rankings (all one-HTTP-call, cached per Client lifetime) ───

    def quality_of_life_rankings(self) -> dict[str, QoLIndices]:
        if self._qol_cache is None:
            url = f"{BASE}/quality-of-life/rankings_by_country.jsp"
            html, _ = self._get_html(url)
            self._qol_cache = parse_qol_rankings(html)
        return self._qol_cache

    def property_rankings_by_country(self) -> dict[str, PropertyIndices]:
        if self._property_country_cache is None:
            url = f"{BASE}/property-investment/rankings_by_country.jsp"
            html, _ = self._get_html(url)
            self._property_country_cache = parse_property_rankings_by_country(html)
        return self._property_country_cache

    def property_rankings_by_city(self) -> dict[str, PropertyIndices]:
        if self._property_city_cache is None:
            url = f"{BASE}/property-investment/rankings.jsp"
            html, _ = self._get_html(url)
            self._property_city_cache = parse_property_rankings_by_city(html)
        return self._property_city_cache

    def crime_rankings(self) -> dict[str, CrimeIndices]:
        if self._crime_cache is None:
            url = f"{BASE}/crime/rankings_by_country.jsp"
            html, _ = self._get_html(url)
            self._crime_cache = parse_crime_rankings(html)
        return self._crime_cache

    def health_care_rankings(self) -> dict[str, HealthCareIndices]:
        if self._health_care_cache is None:
            url = f"{BASE}/health-care/rankings_by_country.jsp"
            html, _ = self._get_html(url)
            self._health_care_cache = parse_health_care_rankings(html)
        return self._health_care_cache

    def pollution_rankings(self) -> dict[str, PollutionIndices]:
        if self._pollution_cache is None:
            url = f"{BASE}/pollution/rankings_by_country.jsp"
            html, _ = self._get_html(url)
            self._pollution_cache = parse_pollution_rankings(html)
        return self._pollution_cache

    def traffic_rankings(self) -> dict[str, TrafficIndices]:
        if self._traffic_cache is None:
            url = f"{BASE}/traffic/rankings_by_country.jsp"
            html, _ = self._get_html(url)
            self._traffic_cache = parse_traffic_rankings(html)
        return self._traffic_cache
