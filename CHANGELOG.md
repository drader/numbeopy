# Changelog

All notable changes to `numbeopy` are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

---

## [Unreleased]

_No unreleased changes._

---

## [0.1.0] — 2026-07-12

**Initial release.** Small standalone Python client for Numbeo's public cost-of-living pages, extracted from the FinO research project's fetcher layer.

### Added

- `numbeopy.Client` — rate-limited HTTP client (default 3s between requests) with polite User-Agent.
- `numbeopy.fetch_country(country, currency="USD")` — full country snapshot: item prices + city indices + country-level aggregate indices.
- `numbeopy.list_countries(currency="USD")` — ordered list of all countries Numbeo publishes on its rankings page (~152 entries).
- `numbeopy.fetch_country_prices()`, `numbeopy.fetch_country_indices()` — convenience wrappers around `fetch_country`.
- `numbeopy.parser.parse_country_page()`, `parse_country_rankings()`, `parse_country_rankings_full()` — pure-function parsers accepting raw HTML (useful for offline tests + custom clients).
- Data model: `Price`, `CityIndices`, `CountryData` (all serialisable via `CountryData.to_dict()`).
- Provenance stamping on every fetch: `source_url`, `source_sha256`, `fetched_at` (ISO-8601 UTC).
- CLI: `numbeopy list-countries` + `numbeopy fetch <country>` with `--currency`, `--rate-limit`, `--no-country-indices`, `--output` flags.
- Offline test suite (`tests/test_parser.py`) with HTML fixtures for Turkey country_result + full rankings pages.
- Optional live smoke test (`tests/test_smoke.py`) gated on `NUMBEOPY_LIVE=1` env var.

### Data coverage per country

- **50+ item prices** across 10 categories (Restaurants, Markets, Transportation, Utilities, Sports And Leisure, Childcare, Clothing And Shoes, Rent Per Month, Buy Apartment Price, Salaries And Financing)
- **3-20 cities** per country with 6 aggregate indices each
- **6 country-level aggregate indices** (Cost of Living, Rent, Cost of Living Plus Rent, Groceries, Restaurant Price, Local Purchasing Power)

### Rationale

Numbeo's [paid API](https://www.numbeo.com/common/api.jsp) starts at $260/month. Existing GitHub scrapers were either unlicensed (Phernando82, mounicmadiraju's Python-2 code, ibrahimaltay), tied to heavy infrastructure (sinanazem — Docker+PostgreSQL), or non-Python (ndenissov — Go). `numbeopy` targets a research use case where a lightweight polite client is enough.

### Not included (future)

- City-level detail fetching (e.g. per-neighborhood rents within a city — Numbeo does publish this on `city_result.jsp` but v0.1.0 stops at country-level snapshots + the city-index summary that appears on country pages).
- Historical time series (Numbeo doesn't expose historical data on public pages; paid API only).
- Persistent caching to disk (a Client instance caches rankings in-memory only for its lifetime).
