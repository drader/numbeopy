# numbeopy

**Python client for [Numbeo](https://www.numbeo.com/cost-of-living/)'s public cost-of-living pages.** Small, rate-limited, dependency-light. Fetches country-level item prices, per-city aggregate indices, and country-level aggregate indices via `pandas.read_html` on Numbeo's public HTML.

**No API key.** No paid subscription. No third-party service. Just polite HTTP.

---

## Install

```bash
pip install numbeopy                  # once published to PyPI
pip install -e /path/to/numbeopy       # from a local checkout
```

Python 3.10+ required. Dependencies: `requests`, `pandas`, `lxml`.

---

## Quick start

```python
import numbeopy

# All countries Numbeo publishes on its rankings page
countries = numbeopy.list_countries()
print(f"{len(countries)} countries")

# Full snapshot for one country: item prices + city indices + country indices
data = numbeopy.fetch_country("Turkey")
print(f"prices: {len(data.prices)}, cities: {len(data.cities)}, indices: {len(data.indices)}")

# JSON dump (framework-friendly)
import json
print(json.dumps(data.to_dict(), indent=2))
```

Or via CLI:

```bash
numbeopy list-countries | head -20
numbeopy fetch Turkey --output turkey.json
numbeopy fetch "United States" --currency USD --rate-limit 2.0 > usa.json
```

---

## What you get per country

| Field | Contents | Source |
|---|---|---|
| `prices` | 50+ item rows: category, item, price, range, currency | `country_result.jsp` Table 1 |
| `cities` | 3-20 city rows: name + 6 aggregate indices | `country_result.jsp` Table 4 |
| `indices` | Country-level: Cost of Living, Rent, Groceries, Restaurant, Local Purchasing Power | `rankings_by_country.jsp` |
| `source_url`, `source_sha256`, `fetched_at` | Provenance metadata | client-side stamp |

`prices[i].category` values: `Restaurants`, `Markets`, `Transportation`, `Utilities`, `Sports And Leisure`, `Childcare`, `Clothing And Shoes`, `Rent Per Month`, `Buy Apartment Price`, `Salaries And Financing`.

---

## Rate limiting

Default 3.0 seconds between HTTP requests, per `Client` instance. Numbeo doesn't publish a specific rate limit for public pages, but 3s is conservative and matches the pattern used by academic data collectors. You can tune it:

```python
from numbeopy import Client
client = Client(rate_limit_seconds=5.0)   # even more polite
data = client.fetch_country(country="Spain")
```

**Please stay polite.** Numbeo runs on donations + subscriptions. Do not run this at high frequency, do not distribute derived data at scale, and prefer their [paid API](https://www.numbeo.com/common/api.jsp) if you need production-grade traffic.

---

## Data source and licensing

Numbeo's data is **crowdsourced** — millions of user-submitted prices with automated market-data collection and statistical validation ([methodology](https://www.numbeo.com/common/motivation_and_methodology.jsp)). It is not validated against national statistical offices. Treat it accordingly:

- ✅ Useful for **cross-country cost-of-living comparisons** where official granularity is missing (item-level basket costs, per-city variations)
- ✅ Useful as an **indicator design reference** for what individual-perspective metrics matter
- ❌ Not suitable as a substitute for official statistical office data on aggregates like national CPI or GDP
- ❌ Not to be republished as a bulk dataset

Numbeo publishes its own data under its [Terms of Use](https://www.numbeo.com/common/terms-of-use.jsp). This client respects that: low request rate, identifying User-Agent, no bulk redistribution. When incorporating Numbeo values into published work, attribute Numbeo as the source and disclose the fetch date.

---

## API reference (short)

### Module-level convenience functions

```python
numbeopy.list_countries(currency: str = "USD") -> list[str]
numbeopy.fetch_country(country: str, currency: str = "USD") -> CountryData
numbeopy.fetch_country_prices(country: str, currency: str = "USD") -> list[Price]
numbeopy.fetch_country_indices(country: str, currency: str = "USD") -> dict[str, float]
```

Each uses a shared default `Client` instance.

### `Client` class

```python
Client(
    rate_limit_seconds: float = 3.0,
    timeout_seconds: float = 30.0,
    user_agent: str = "numbeopy/0.1 ...",
    session: requests.Session | None = None,
)
```

Methods: `list_countries()`, `country_indices(country)`, `fetch_country(country, include_country_indices=True)`.

### Data model

```python
@dataclass(frozen=True)
class Price:
    category: str
    item: str
    price: float
    range_low: float | None
    range_high: float | None
    currency: str = "USD"
    has_price: bool = True

@dataclass(frozen=True)
class CityIndices:
    city: str
    cost_of_living_index: float | None
    rent_index: float | None
    cost_of_living_plus_rent_index: float | None
    groceries_index: float | None
    restaurant_price_index: float | None
    local_purchasing_power_index: float | None

@dataclass
class CountryData:
    country: str
    currency: str
    prices: list[Price]
    cities: list[CityIndices]
    indices: dict[str, float]
    fetched_at: str            # ISO-8601 UTC timestamp
    source_url: str
    source_sha256: str

    def to_dict(self) -> dict     # JSON-ready
```

---

## Tests

```bash
pip install -e ".[dev]"
pytest                              # offline tests (fixture-based)
NUMBEOPY_LIVE=1 pytest              # includes live-network smoke test
```

Fixtures under `tests/fixtures/` are captured HTML from real Numbeo pages; the offline tests assert parser correctness against them.

---

## Origin

Extracted from the FinO (financial infographics) research project's fetcher layer. Kept as a standalone library so it can be reused independently by any project needing polite, structured access to Numbeo's public data.

## License

CC BY-NC 4.0 — see [LICENSE](LICENSE). Free for non-commercial use with attribution.
