"""numbeopy — HTTP client with rate limiting.

The `Client` class fetches Numbeo public HTML pages and hands them to
`numbeopy.parser`. All requests share a per-instance rate limiter (default 3s
between requests) and a polite User-Agent identifying the client.

Public pages targeted:
    country_result.jsp?country=<X>          → item prices + city indices
    rankings_by_country.jsp                 → country-level aggregate indices
"""
from __future__ import annotations

import hashlib
import time
from urllib.parse import quote_plus

import requests

from numbeopy.models import CountryData
from numbeopy.parser import (
    parse_country_page,
    parse_country_rankings,
    parse_country_rankings_full,
)

DEFAULT_RATE_LIMIT_SECONDS: float = 3.0
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_USER_AGENT: str = "numbeopy/0.1 (+https://github.com/drader/numbeopy)"

BASE_URL = "https://www.numbeo.com/cost-of-living"


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

    # ─── Rankings (country-level aggregate indices) ───

    def _rankings_full(self, currency: str) -> dict[str, dict[str, float]]:
        if currency not in self._rankings_cache:
            url = f"{BASE_URL}/rankings_by_country.jsp?displayCurrency={currency}"
            html, _ = self._get_html(url)
            self._rankings_cache[currency] = parse_country_rankings_full(html)
        return self._rankings_cache[currency]

    def list_countries(self, *, currency: str = "USD") -> list[str]:
        """Return ordered list of country names Numbeo publishes on rankings page."""
        rankings = self._rankings_full(currency=currency)
        return list(rankings.keys())

    def country_indices(self, country: str, *, currency: str = "USD") -> dict[str, float]:
        """Return country-level aggregate indices (from rankings page cache)."""
        rankings = self._rankings_full(currency=currency)
        return dict(rankings.get(country, {}))

    # ─── Country snapshot (prices + city indices + country indices) ───

    def fetch_country(
        self,
        *,
        country: str,
        currency: str = "USD",
        include_country_indices: bool = True,
    ) -> CountryData:
        encoded = quote_plus(country)
        url = f"{BASE_URL}/country_result.jsp?country={encoded}&displayCurrency={currency}"
        html, sha = self._get_html(url)
        data = parse_country_page(html, country=country, currency=currency)
        data.source_url = url
        data.source_sha256 = sha
        if include_country_indices:
            data.indices = self.country_indices(country, currency=currency)
        return data
