# Changelog

All notable changes to `numbeopy` are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

---

## [Unreleased]

_No unreleased changes._

---

## [0.2.0] — 2026-07-12

**Theme**: full aggregate-view coverage. Non-breaking additive release.

Adds all six of Numbeo's category-level ranking pages (Quality of Life, Property, Crime, Health Care, Pollution, Traffic) plus city-level cost-of-living fetch. Every publicly-published Numbeo aggregate view is now accessible via a single Python API call. Bulk-crawler over all 12,790 city pages is **deliberately not included** — a research-safe design boundary explained in the README.

### Added

- `Client.fetch_city(country, city)` → `CityData` — city-level cost-of-living prices via `city_result.jsp` (~50-70 items per city).
- `Client.quality_of_life_rankings()` → `dict[country, QoLIndices]` from `quality-of-life/rankings_by_country.jsp` (89+ countries × 9 fields: Quality of Life, Purchasing Power, Safety, Health Care, Cost of Living, Property Price to Income, Traffic Commute Time, Pollution, Climate).
- `Client.property_rankings_by_country()` → `dict[country, PropertyIndices]` from `property-investment/rankings_by_country.jsp` (108+ countries × 7 metrics).
- `Client.property_rankings_by_city()` → `dict[city, PropertyIndices]` from `property-investment/rankings.jsp` (393+ cities).
- `Client.crime_rankings()` → `dict[country, CrimeIndices]` (148+ countries × Crime + Safety indices).
- `Client.health_care_rankings()` → `dict[country, HealthCareIndices]` (101+ countries × Health Care + Health Care Expenditure indices).
- `Client.pollution_rankings()` → `dict[country, PollutionIndices]` (117+ countries × Pollution + Exp Pollution indices).
- `Client.traffic_rankings()` → `dict[country, TrafficIndices]` (89+ countries × Traffic, Time, Time Exp, Inefficiency indices).
- `fetch_country(..., include_all_categories=True)` — convenience that populates all six category indices on the returned `CountryData` in one call (7 HTTP requests total, ~21s under default 3s rate limit).
- Per-category rankings cached per `Client` instance — subsequent calls to the same ranking method are free.
- Module-level convenience wrappers for all new methods (`numbeopy.fetch_city`, `numbeopy.quality_of_life_rankings`, etc.).
- CLI subcommands:
  - `numbeopy fetch-city <country> <city>` — single-city snapshot
  - `numbeopy fetch <country> --all` — country + all 6 category indices
  - `numbeopy rankings <category>` — one of `quality-of-life`, `property` (with `--by-city`), `crime`, `health-care`, `pollution`, `traffic`
- New dataclasses: `CityData`, `QoLIndices`, `PropertyIndices`, `CrimeIndices`, `HealthCareIndices`, `PollutionIndices`, `TrafficIndices`.
- New parsers (`parse_city_page`, `parse_qol_rankings`, `parse_property_rankings_by_country`, `parse_property_rankings_by_city`, `parse_crime_rankings`, `parse_health_care_rankings`, `parse_pollution_rankings`, `parse_traffic_rankings`) — all pure functions accepting raw HTML, usable independently from `Client`.
- 8 new HTML fixtures + **9 new parser test classes** (13 new tests) + new `tests/test_client.py` with mocked-session cache/provenance tests (4 tests). Total offline suite: 23 (was 10). Live smoke: 10.

### Changed

- `CountryData` gained optional fields: `qol`, `property`, `crime`, `health_care`, `pollution`, `traffic` — all `None` by default; populated when `fetch_country(..., include_all_categories=True)` is called. **Backward-compatible**: existing v0.1.0 code that only reads `prices`, `cities`, `indices` continues to work.
- `Client` cache now includes per-category ranking caches (in-memory, per instance).
- User-Agent bumped to `numbeopy/0.2 (+https://github.com/drader/numbeopy)`.

### Not added — deliberate design boundary

- **Bulk fetch of all 12,790 city pages** is not shipped. Rationale:
  - Full sweep at 3s/request = ~10.6 hours → cache always stale, real-time crowdsourced source
  - Systematic bulk crawler on a public repo would trigger Numbeo's anti-scraping filters + create legal exposure via c-and-d risk
  - Callers who need city-level detail for many cities can loop `fetch_city()` themselves and own the risk
- **Historical time series** — Numbeo doesn't publish these on public pages; paid API only.

### Coverage summary

Every publicly-published Numbeo aggregate view is now reachable via a single call:

| Numbeo section | Method | Result |
|---|---|---|
| Cost of Living (country) | `fetch_country(x)` | prices + city index summary + country COL indices |
| Cost of Living (city) | `fetch_city(country, city)` | prices for one city |
| Quality of Life | `quality_of_life_rankings()` | 89+ countries × 9 fields |
| Property (country) | `property_rankings_by_country()` | 108+ countries × 7 fields |
| Property (city) | `property_rankings_by_city()` | 393+ cities × 7 fields |
| Crime / Safety | `crime_rankings()` | 148+ countries |
| Health Care | `health_care_rankings()` | 101+ countries |
| Pollution | `pollution_rankings()` | 117+ countries |
| Traffic | `traffic_rankings()` | 89+ countries |

### Test results

- `pytest -v` → **23/23 offline passed** (was 10/10 in v0.1.0), 10 skipped (live-gated)
- `NUMBEOPY_LIVE=1 pytest` → live smoke suite expanded to 10 tests (was 2), all passing on a fresh Numbeo request budget
- CLI end-to-end: `numbeopy fetch Turkey --all` → 64 prices + 8 cities + 6 COL indices + 6 category indices covering 25+ additional numeric metrics in 7 HTTP calls.

---

## [0.1.0] — 2026-07-12

**Initial release.** Small standalone Python client for Numbeo's public cost-of-living pages, extracted from the FinO research project's fetcher layer.

### Added

- `numbeopy.Client` — rate-limited HTTP client (default 3s between requests) with polite User-Agent.
- `numbeopy.fetch_country(country, currency="USD")` — full country snapshot: item prices + city indices + country-level aggregate indices.
- `numbeopy.list_countries(currency="USD")` — ordered list of all countries Numbeo publishes on its rankings page (~152 entries).
- `numbeopy.fetch_country_prices()`, `numbeopy.fetch_country_indices()` — convenience wrappers.
- `numbeopy.parser.parse_country_page()`, `parse_country_rankings()`, `parse_country_rankings_full()` — pure-function parsers.
- Data model: `Price`, `CityIndices`, `CountryData` (JSON-serialisable via `to_dict()`).
- Provenance stamping on every fetch: `source_url`, `source_sha256`, `fetched_at`.
- CLI: `numbeopy list-countries` + `numbeopy fetch <country>`.
- Offline test suite (10 tests, HTML fixtures for Turkey + rankings).
- Live smoke test (2 tests, gated on `NUMBEOPY_LIVE=1`).
