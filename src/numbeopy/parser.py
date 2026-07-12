"""numbeopy — HTML → dataclass parsers.

Every Numbeo public page consumed by numbeopy is a conventional HTML page
containing tables that `pandas.read_html` handles cleanly. This module
normalises the raw DataFrames into typed numbeopy dataclasses, handling
Numbeo-specific quirks:

    - the price column's header is literally "Edit" (the button text at column top)
    - the first column mixes category headers with item rows
    - price cells look like "$8.51"; range cells look like "5.32-14.90"
    - some cells are "?" (unpopulated) or empty
    - ranking pages consistently place the main table at index [1] with
      Rank as the first column
"""
from __future__ import annotations

import re
from io import StringIO
from typing import Any, Callable

import pandas as pd

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


# Regexes for parsing Numbeo cell content
_PRICE_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")
_RANGE_RE = re.compile(r"([-+]?\d[\d,]*\.?\d*)\s*[-–]\s*([-+]?\d[\d,]*\.?\d*)")


def _clean_number(cell: Any) -> float | None:
    """Extract a float from a Numbeo cell. Returns None if unparseable / '?' / blank."""
    if cell is None:
        return None
    text = str(cell).strip()
    if not text or text in ("?", "-", "nan", "NaN", "Edit"):
        return None
    text = text.replace(",", "").replace(" ", " ")
    match = _PRICE_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_range(cell: Any) -> tuple[float | None, float | None]:
    if cell is None:
        return None, None
    text = str(cell).strip()
    match = _RANGE_RE.search(text)
    if not match:
        return None, None
    try:
        return float(match.group(1).replace(",", "")), float(match.group(2).replace(",", ""))
    except ValueError:
        return None, None


# ═══════════════════════════════════════════════════════════════════════
# country_result.jsp and city_result.jsp — prices table
# ═══════════════════════════════════════════════════════════════════════

_CATEGORY_TOKENS = {
    "Restaurants", "Markets", "Transportation", "Utilities (Monthly)",
    "Sports And Leisure", "Childcare", "Clothing And Shoes",
    "Rent Per Month", "Buy Apartment Price", "Salaries And Financing",
}


def _looks_like_category_header(text: str) -> bool:
    text = text.strip()
    if text in _CATEGORY_TOKENS:
        return True
    if not text or len(text) > 40 or any(ch.isdigit() for ch in text):
        return False
    if "," in text or "." in text:
        return False
    words = text.split()
    if not (1 <= len(words) <= 5):
        return False
    return all(w[:1].isupper() for w in words if w)


def _is_prices_table(df: pd.DataFrame) -> bool:
    """Prices table: 3 cols, second col named 'Edit', third col 'Range'."""
    if df.shape[1] != 3:
        return False
    cols = [str(c) for c in df.columns]
    return "Edit" in cols and "Range" in cols


def _is_cities_table(df: pd.DataFrame) -> bool:
    cols = [str(c) for c in df.columns]
    return "City" in cols and any("Cost of Living Index" in c for c in cols)


def _extract_prices(df: pd.DataFrame, *, currency: str) -> list[Price]:
    prices: list[Price] = []
    current_category: str = ""
    cols = list(df.columns)
    item_col, price_col, range_col = cols[0], cols[1], cols[2]

    for _, row in df.iterrows():
        item = str(row[item_col]).strip()
        price = _clean_number(row[price_col])
        if price is None:
            if _looks_like_category_header(item):
                current_category = item
                continue
            low, high = _parse_range(row[range_col])
            prices.append(Price(
                category=current_category or str(item_col), item=item, price=0.0,
                range_low=low, range_high=high, currency=currency, has_price=False,
            ))
            continue
        low, high = _parse_range(row[range_col])
        prices.append(Price(
            category=current_category or str(item_col), item=item, price=price,
            range_low=low, range_high=high, currency=currency, has_price=True,
        ))
    return prices


def _extract_cities(df: pd.DataFrame) -> list[CityIndices]:
    cities: list[CityIndices] = []
    for _, row in df.iterrows():
        city = str(row.get("City", "")).strip()
        if not city or city.lower() == "nan":
            continue
        cities.append(CityIndices(
            city=city,
            cost_of_living_index=_clean_number(row.get("Cost of Living Index")),
            rent_index=_clean_number(row.get("Rent Index")),
            cost_of_living_plus_rent_index=_clean_number(row.get("Cost of Living Plus Rent Index")),
            groceries_index=_clean_number(row.get("Groceries Index")),
            restaurant_price_index=_clean_number(row.get("Restaurant Price Index")),
            local_purchasing_power_index=_clean_number(row.get("Local Purchasing Power Index")),
        ))
    return cities


def parse_country_page(html: str, *, country: str, currency: str = "USD") -> CountryData:
    """Parse a country_result.jsp page into a CountryData snapshot (prices + city indices)."""
    dfs = pd.read_html(StringIO(html))
    data = CountryData(country=country, currency=currency)
    for df in dfs:
        if _is_prices_table(df):
            data.prices = _extract_prices(df, currency=currency)
        elif _is_cities_table(df):
            data.cities = _extract_cities(df)
    return data


def parse_city_page(html: str, *, country: str, city: str, currency: str = "USD") -> CityData:
    """Parse a city_result.jsp page into a CityData snapshot (prices only)."""
    dfs = pd.read_html(StringIO(html))
    data = CityData(country=country, city=city, currency=currency)
    for df in dfs:
        if _is_prices_table(df):
            data.prices = _extract_prices(df, currency=currency)
            break
    return data


# ═══════════════════════════════════════════════════════════════════════
# rankings_by_country.jsp (cost-of-living aggregate indices)
# ═══════════════════════════════════════════════════════════════════════

def parse_country_rankings(html: str) -> list[str]:
    """Ordered list of country names from the cost-of-living rankings page."""
    dfs = pd.read_html(StringIO(html))
    for df in dfs:
        cols = [str(c) for c in df.columns]
        if "Country" in cols and any("Cost of Living Index" in c for c in cols):
            names = [str(x).strip() for x in df["Country"].tolist()]
            return [n for n in names if n and n.lower() != "nan"]
    return []


def parse_country_rankings_full(html: str) -> dict[str, dict[str, float]]:
    """{ country_name: { index_name: value, ... } } from the cost-of-living rankings page."""
    dfs = pd.read_html(StringIO(html))
    for df in dfs:
        cols = [str(c) for c in df.columns]
        if "Country" not in cols:
            continue
        if not any("Cost of Living Index" in c for c in cols):
            continue
        return _rows_to_dict(df, key_col="Country", drop=("Rank",))
    return {}


# ═══════════════════════════════════════════════════════════════════════
# Generic ranking parser + typed wrappers
# ═══════════════════════════════════════════════════════════════════════

def _rows_to_dict(df: pd.DataFrame, *, key_col: str, drop: tuple[str, ...] = ()) -> dict[str, dict[str, float]]:
    """Transform a ranking DataFrame into { key: { col: numeric_value } }."""
    out: dict[str, dict[str, float]] = {}
    cols = [str(c) for c in df.columns]
    for _, row in df.iterrows():
        key = str(row.get(key_col, "")).strip()
        if not key or key.lower() == "nan":
            continue
        indices: dict[str, float] = {}
        for col in cols:
            if col == key_col or col in drop:
                continue
            val = _clean_number(row.get(col))
            if val is not None:
                indices[col] = val
        out[key] = indices
    return out


def _find_ranking_table(html: str, *, key_col: str, required_col_substr: str) -> pd.DataFrame | None:
    """Locate the ranking table in the page (usually Table[1])."""
    dfs = pd.read_html(StringIO(html))
    for df in dfs:
        cols = [str(c) for c in df.columns]
        if key_col in cols and any(required_col_substr in c for c in cols):
            return df
    return None


def _build_typed(rows: dict[str, dict[str, float]], key_field: str, dc_cls: type,
                 column_map: dict[str, str]) -> dict[str, Any]:
    """Convert `_rows_to_dict` output into typed dataclasses.

    `column_map` maps Numbeo column names (as they appear in the DataFrame)
    to the dataclass field names. Unmapped columns are collected in `extras`
    when the dataclass supports it.
    """
    typed: dict[str, Any] = {}
    dc_fields = {f for f in dc_cls.__dataclass_fields__ if f != "extras"}
    has_extras = "extras" in dc_cls.__dataclass_fields__
    for key, cell_dict in rows.items():
        kwargs: dict[str, Any] = {key_field: key}
        extras: dict[str, float] = {}
        for col, value in cell_dict.items():
            field_name = column_map.get(col)
            if field_name and field_name in dc_fields:
                kwargs[field_name] = value
            elif has_extras:
                extras[col] = value
        if has_extras:
            kwargs["extras"] = extras
        typed[key] = dc_cls(**kwargs)
    return typed


# ─── Quality of Life ───

_QOL_COL_MAP = {
    "Quality of Life Index": "quality_of_life_index",
    "Purchasing Power Index": "purchasing_power_index",
    "Safety Index": "safety_index",
    "Health Care Index": "health_care_index",
    "Cost of Living Index": "cost_of_living_index",
    "Property Price to Income Ratio": "property_price_to_income_ratio",
    "Traffic Commute Time Index": "traffic_commute_time_index",
    "Pollution Index": "pollution_index",
    "Climate Index": "climate_index",
}


def parse_qol_rankings(html: str) -> dict[str, QoLIndices]:
    df = _find_ranking_table(html, key_col="Country", required_col_substr="Quality of Life Index")
    if df is None:
        return {}
    rows = _rows_to_dict(df, key_col="Country", drop=("Rank",))
    return _build_typed(rows, key_field="country", dc_cls=QoLIndices, column_map=_QOL_COL_MAP)


# ─── Property (country and city) ───

_PROPERTY_COL_MAP = {
    "Price To Income Ratio": "price_to_income_ratio",
    "Gross Rental Yield City Centre": "gross_rental_yield_city_centre",
    "Gross Rental Yield Outside of Centre": "gross_rental_yield_outside_centre",
    "Price To Rent Ratio City Centre": "price_to_rent_ratio_city_centre",
    "Price To Rent Ratio Outside Of Centre": "price_to_rent_ratio_outside_centre",
    "Mortgage As A Percentage Of Income": "mortgage_as_percentage_of_income",
    "Affordability Index": "affordability_index",
}


def parse_property_rankings_by_country(html: str) -> dict[str, PropertyIndices]:
    df = _find_ranking_table(html, key_col="Country", required_col_substr="Price To Income Ratio")
    if df is None:
        return {}
    rows = _rows_to_dict(df, key_col="Country", drop=("Rank",))
    typed = _build_typed(rows, key_field="location", dc_cls=PropertyIndices, column_map=_PROPERTY_COL_MAP)
    # scope defaults to "country" (dataclass default), no need to override
    return typed


def parse_property_rankings_by_city(html: str) -> dict[str, PropertyIndices]:
    df = _find_ranking_table(html, key_col="City", required_col_substr="Price To Income Ratio")
    if df is None:
        return {}
    rows = _rows_to_dict(df, key_col="City", drop=("Rank",))
    return {
        city: PropertyIndices(
            location=obj.location, scope="city",
            price_to_income_ratio=obj.price_to_income_ratio,
            gross_rental_yield_city_centre=obj.gross_rental_yield_city_centre,
            gross_rental_yield_outside_centre=obj.gross_rental_yield_outside_centre,
            price_to_rent_ratio_city_centre=obj.price_to_rent_ratio_city_centre,
            price_to_rent_ratio_outside_centre=obj.price_to_rent_ratio_outside_centre,
            mortgage_as_percentage_of_income=obj.mortgage_as_percentage_of_income,
            affordability_index=obj.affordability_index,
            extras=obj.extras,
        )
        for city, obj in _build_typed(
            rows, key_field="location", dc_cls=PropertyIndices, column_map=_PROPERTY_COL_MAP,
        ).items()
    }


# ─── Crime ───

def parse_crime_rankings(html: str) -> dict[str, CrimeIndices]:
    df = _find_ranking_table(html, key_col="Country", required_col_substr="Crime Index")
    if df is None:
        return {}
    return _build_typed(
        _rows_to_dict(df, key_col="Country", drop=("Rank",)),
        key_field="country", dc_cls=CrimeIndices,
        column_map={"Crime Index": "crime_index", "Safety Index": "safety_index"},
    )


# ─── Health Care ───

def parse_health_care_rankings(html: str) -> dict[str, HealthCareIndices]:
    df = _find_ranking_table(html, key_col="Country", required_col_substr="Health Care Index")
    if df is None:
        return {}
    return _build_typed(
        _rows_to_dict(df, key_col="Country", drop=("Rank",)),
        key_field="country", dc_cls=HealthCareIndices,
        column_map={"Health Care Index": "health_care_index", "Health Care Exp. Index": "health_care_exp_index"},
    )


# ─── Pollution ───

def parse_pollution_rankings(html: str) -> dict[str, PollutionIndices]:
    df = _find_ranking_table(html, key_col="Country", required_col_substr="Pollution Index")
    if df is None:
        return {}
    return _build_typed(
        _rows_to_dict(df, key_col="Country", drop=("Rank",)),
        key_field="country", dc_cls=PollutionIndices,
        column_map={"Pollution Index": "pollution_index", "Exp Pollution Index": "exp_pollution_index"},
    )


# ─── Traffic ───

def parse_traffic_rankings(html: str) -> dict[str, TrafficIndices]:
    df = _find_ranking_table(html, key_col="Country", required_col_substr="Traffic Index")
    if df is None:
        return {}
    return _build_typed(
        _rows_to_dict(df, key_col="Country", drop=("Rank",)),
        key_field="country", dc_cls=TrafficIndices,
        column_map={
            "Traffic Index": "traffic_index",
            "Time Index (in minutes)": "time_index_minutes",
            "Time Exp. Index": "time_exp_index",
            "Inefficiency Index": "inefficiency_index",
        },
    )
