# numbeopy

**Python client for [Numbeo](https://www.numbeo.com/cost-of-living/)'s public pages.** Covers every aggregate view Numbeo publishes: cost-of-living prices (country + city), quality of life, property investment, crime, health care, pollution, traffic. Rate-limited, dependency-light, one Python API call per view.

**No API key.** No paid subscription. No third-party service. Just polite HTTP with `pandas.read_html`.

---

## Install

```bash
pip install numbeopy                   # once published to PyPI
pip install -e /path/to/numbeopy       # from a local checkout
```

Python 3.10+. Dependencies: `requests`, `pandas`, `lxml`.

---

## Quick start

```python
import numbeopy

# One-line country snapshot: prices + city indices + country COL indices
data = numbeopy.fetch_country("Turkey")
print(f"{len(data.prices)} prices, {len(data.cities)} cities, {len(data.indices)} COL indices")

# Full snapshot including all 6 category indices (7 HTTP calls total, ~21s)
full = numbeopy.fetch_country("Turkey", include_all_categories=True)
print(full.qol.quality_of_life_index, full.property.price_to_income_ratio)
print(full.crime.crime_index, full.pollution.pollution_index)

# City-level detail for one specific city
istanbul = numbeopy.fetch_city("Turkey", "Istanbul")

# Category rankings (all countries in one call, cached per Client instance)
qol = numbeopy.quality_of_life_rankings()          # dict[country, QoLIndices]
property_country = numbeopy.property_rankings_by_country()
property_city = numbeopy.property_rankings_by_city()
crime = numbeopy.crime_rankings()
health = numbeopy.health_care_rankings()
pollution = numbeopy.pollution_rankings()
traffic = numbeopy.traffic_rankings()
```

Or via CLI:

```bash
numbeopy list-countries | head -20
numbeopy fetch Turkey --all --output turkey-full.json
numbeopy fetch-city Turkey Istanbul --output istanbul.json
numbeopy rankings quality-of-life > qol.json
numbeopy rankings property --by-city > property-cities.json
numbeopy rankings crime > crime.json
```

---

## What you get

### Per country — `fetch_country(country, include_all_categories=True)`

| Field | Contents | Source page |
|---|---|---|
| `prices` | 50-70 item rows: category, item, price, range, currency | `cost-of-living/country_result.jsp` |
| `cities` | 3-20 city rows: name + 6 aggregate indices | (same page, city-index table) |
| `indices` | Country COL: Cost of Living, Rent, Groceries, Restaurant, Local Purchasing Power (6 indices) | `cost-of-living/rankings_by_country.jsp` |
| `qol` | Quality of Life composite: QoL Index, Purchasing Power, Safety, Health Care, Cost of Living, Property Price to Income, Traffic Commute Time, Pollution, Climate (9 indices) | `quality-of-life/rankings_by_country.jsp` |
| `property` | Price to Income, Gross Rental Yield (centre/outside), Price to Rent (centre/outside), Mortgage as % of Income, Affordability Index (7 metrics) | `property-investment/rankings_by_country.jsp` |
| `crime` | Crime Index, Safety Index | `crime/rankings_by_country.jsp` |
| `health_care` | Health Care Index, Health Care Expenditure Index | `health-care/rankings_by_country.jsp` |
| `pollution` | Pollution Index, Exp Pollution Index | `pollution/rankings_by_country.jsp` |
| `traffic` | Traffic Index, Time Index (minutes), Time Exp Index, Inefficiency Index | `traffic/rankings_by_country.jsp` |
| `source_url`, `source_sha256`, `fetched_at` | Provenance | client-side stamp |

Price categories in `prices`: `Restaurants`, `Markets`, `Transportation`, `Utilities (Monthly)`, `Sports And Leisure`, `Childcare`, `Clothing And Shoes`, `Rent Per Month`, `Buy Apartment Price`, `Salaries And Financing`.

### Per city — `fetch_city(country, city)`

Same 50-70 item price table as country-level, but averaged over one specific city instead of country. Returns `CityData` with `prices`, `country`, `city`, provenance stamps.

### Category-only rankings

Each category ranking is one HTTP call returning `dict[key, TypedIndices]`. Cached per `Client` instance — subsequent calls to the same method are free.

---

## Rate limiting

Default 3.0 seconds between HTTP requests per `Client` instance. Tunable:

```python
from numbeopy import Client
client = Client(rate_limit_seconds=5.0)
data = client.fetch_country(country="Spain")
```

**Please stay polite.** Numbeo runs on donations + subscriptions. Do not run at high frequency, do not distribute derived data at scale, and prefer their [paid API](https://www.numbeo.com/common/api.jsp) for production traffic.

---

## What numbeopy does NOT do (by design)

- **Bulk fetch of all 12,790 city pages.** A systematic city-by-city crawler would take ~10 hours per pass (real-time crowdsourced data → cache always stale), trigger Numbeo's anti-scraping filters, and put the client repo at legal risk. Callers who need city-level detail for many cities can loop `fetch_city()` themselves.
- **Historical time series.** Numbeo doesn't publish historical prices on public pages — paid API only.
- **Individual crowdsourced submissions.** Numbeo's "9.8M prices" number counts total contributor submissions to date; only aggregated averages are on public pages.

---

## Data source and licensing

Numbeo's data is **crowdsourced** — [millions of user-submitted prices with automated market-data collection and statistical validation](https://www.numbeo.com/common/motivation_and_methodology.jsp). It is not validated against national statistical offices. Treat it accordingly:

- ✅ Useful for **cross-country cost-of-living comparisons** where official granularity is missing (item-level basket costs, per-city variations, cross-category composite indices)
- ✅ Useful as an **indicator-design reference** for what individual-perspective metrics matter
- ❌ Not suitable as a substitute for official statistical office data on aggregates like national CPI or GDP
- ❌ Not to be republished as a bulk dataset

Numbeo publishes its own data under its [Terms of Use](https://www.numbeo.com/common/terms-of-use.jsp). This client respects that: low request rate, identifying User-Agent, no bulk redistribution. When incorporating Numbeo values into published work, attribute Numbeo as the source and disclose the fetch date.

---

## API reference

### Module-level convenience functions

```python
numbeopy.list_countries(currency="USD") -> list[str]
numbeopy.fetch_country(country, currency="USD", include_all_categories=False) -> CountryData
numbeopy.fetch_country_prices(country, currency="USD") -> list[Price]
numbeopy.fetch_country_indices(country, currency="USD") -> dict[str, float]
numbeopy.fetch_city(country, city, currency="USD") -> CityData

numbeopy.quality_of_life_rankings() -> dict[str, QoLIndices]
numbeopy.property_rankings_by_country() -> dict[str, PropertyIndices]
numbeopy.property_rankings_by_city() -> dict[str, PropertyIndices]
numbeopy.crime_rankings() -> dict[str, CrimeIndices]
numbeopy.health_care_rankings() -> dict[str, HealthCareIndices]
numbeopy.pollution_rankings() -> dict[str, PollutionIndices]
numbeopy.traffic_rankings() -> dict[str, TrafficIndices]
```

All use a shared default `Client` instance.

### `Client` class

```python
Client(
    rate_limit_seconds: float = 3.0,
    timeout_seconds: float = 30.0,
    user_agent: str = "numbeopy/0.2 (+https://github.com/drader/numbeopy)",
    session: requests.Session | None = None,
)
```

Every ranking method on `Client` caches its result per-instance — re-calling `client.quality_of_life_rankings()` a second time is free.

### Dataclasses

`Price`, `CityIndices`, `CountryData`, `CityData`, `QoLIndices`, `PropertyIndices`, `CrimeIndices`, `HealthCareIndices`, `PollutionIndices`, `TrafficIndices`. All JSON-serialisable (either directly or via `to_dict()`).

---

## Tests

```bash
pip install -e ".[dev]"
pytest                              # offline (fixture-based), 23 tests
NUMBEOPY_LIVE=1 pytest              # + 10 live smoke tests against Numbeo
```

Fixtures under `tests/fixtures/` are captured HTML from real Numbeo pages; offline tests assert parser correctness against them.

---

## Origin

Extracted from the FinO (financial infographics) research project's fetcher layer. Kept as a standalone library so it can be reused independently by any project needing polite, structured access to Numbeo's public aggregate data.

## License

CC BY-NC 4.0 — see [LICENSE](LICENSE). Free for non-commercial use with attribution.
