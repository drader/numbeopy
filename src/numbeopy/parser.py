"""numbeopy — HTML → dataclass parsers.

Numbeo pages are conventional HTML with well-formed tables — pandas.read_html
handles the extraction. This module normalises the raw DataFrames into
numbeopy dataclasses, handling the small quirks:

    - the price column's header is literally "Edit" (the button text at column top)
    - the first column mixes category headers with item rows
    - price cells look like "$8.51"; range cells look like "5.32-14.90"
    - some cells are "?" (unpopulated crowdsourced items) or empty
"""
from __future__ import annotations

import re
from io import StringIO
from typing import Any

import pandas as pd

from numbeopy.models import CityIndices, CountryData, Price

# Regexes for parsing Numbeo cell content
_PRICE_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")
_RANGE_RE = re.compile(r"([-+]?\d[\d,]*\.?\d*)\s*[-–]\s*([-+]?\d[\d,]*\.?\d*)")


def _clean_number(cell: Any) -> float | None:
    """Extract a float from a Numbeo price cell. Returns None if unparseable / '?' / blank."""
    if cell is None:
        return None
    text = str(cell).strip()
    if not text or text in ("?", "-", "nan", "NaN", "Edit"):
        return None
    text = text.replace(",", "").replace(" ", " ")
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
# country_result.jsp
# ═══════════════════════════════════════════════════════════════════════

def parse_country_page(html: str, *, country: str, currency: str = "USD") -> CountryData:
    """Parse a country_result.jsp page into a CountryData snapshot.

    Extracts:
      - Table with 3 cols where first col is an item name and second is a price
        → prices list (categories are inferred from single-cell rows)
      - Table with 8 cols starting with "Rank/City" → cities list
    """
    dfs = pd.read_html(StringIO(html))
    data = CountryData(country=country, currency=currency)

    for df in dfs:
        if _is_prices_table(df):
            data.prices = _extract_prices(df, currency=currency)
        elif _is_cities_table(df):
            data.cities = _extract_cities(df)

    return data


def _is_prices_table(df: pd.DataFrame) -> bool:
    """Prices table: 3 cols, second col named 'Edit', third col named 'Range'."""
    if df.shape[1] != 3:
        return False
    cols = [str(c) for c in df.columns]
    return "Edit" in cols and "Range" in cols


def _is_cities_table(df: pd.DataFrame) -> bool:
    """Cities table: has 'City' and 'Cost of Living Index' columns."""
    cols = [str(c) for c in df.columns]
    return "City" in cols and any("Cost of Living Index" in c for c in cols)


def _extract_prices(df: pd.DataFrame, *, currency: str) -> list[Price]:
    prices: list[Price] = []
    current_category: str = ""
    cols = list(df.columns)
    item_col, price_col, range_col = cols[0], cols[1], cols[2]

    for _, row in df.iterrows():
        item = str(row[item_col]).strip()
        price_cell = row[price_col]
        # A "category header" row often has the category name in the item column
        # AND a NaN or empty price. But Numbeo's first column IS the category name
        # of the whole column too. We treat rows without a parseable price as
        # category markers only when their item text equals the current column-header
        # style (e.g. "Restaurants", "Markets"). The simpler heuristic:
        # if the item text contains no comma and no lowercase word AND price is NaN,
        # treat it as a category header. Otherwise even without a price it's an item.
        price = _clean_number(price_cell)
        if price is None:
            # If it looks like a category header, capture it and skip
            if _looks_like_category_header(item):
                current_category = item
                continue
            # Otherwise it's an item with an unpopulated price
            low, high = _parse_range(row[range_col])
            prices.append(Price(
                category=current_category or str(item_col),
                item=item,
                price=0.0,
                range_low=low,
                range_high=high,
                currency=currency,
                has_price=False,
            ))
            continue
        low, high = _parse_range(row[range_col])
        prices.append(Price(
            category=current_category or str(item_col),
            item=item,
            price=price,
            range_low=low,
            range_high=high,
            currency=currency,
            has_price=True,
        ))
    return prices


_CATEGORY_TOKENS = {
    "Restaurants", "Markets", "Transportation", "Utilities (Monthly)",
    "Sports And Leisure", "Childcare", "Clothing And Shoes",
    "Rent Per Month", "Buy Apartment Price", "Salaries And Financing",
}


def _looks_like_category_header(text: str) -> bool:
    text = text.strip()
    if text in _CATEGORY_TOKENS:
        return True
    # Fallback for future Numbeo category renames: short line, no digits,
    # no comma, Title Case, no more than a handful of words. Category names
    # are always short section headers like "Restaurants" or "Rent Per Month".
    if not text or len(text) > 40 or any(ch.isdigit() for ch in text):
        return False
    if "," in text or "." in text:
        return False
    words = text.split()
    if not (1 <= len(words) <= 5):
        return False
    return all(w[:1].isupper() for w in words if w)


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


# ═══════════════════════════════════════════════════════════════════════
# rankings_by_country.jsp
# ═══════════════════════════════════════════════════════════════════════

def parse_country_rankings(html: str) -> list[str]:
    """Return the ordered list of country names from the rankings_by_country page."""
    dfs = pd.read_html(StringIO(html))
    for df in dfs:
        cols = [str(c) for c in df.columns]
        if "Country" in cols and any("Cost of Living Index" in c for c in cols):
            names = [str(x).strip() for x in df["Country"].tolist()]
            return [n for n in names if n and n.lower() != "nan"]
    return []


def parse_country_rankings_full(html: str) -> dict[str, dict[str, float]]:
    """Return { country_name: { index_name: value, ... }, ... } from the rankings page."""
    dfs = pd.read_html(StringIO(html))
    out: dict[str, dict[str, float]] = {}
    for df in dfs:
        cols = [str(c) for c in df.columns]
        if "Country" not in cols:
            continue
        if not any("Cost of Living Index" in c for c in cols):
            continue
        for _, row in df.iterrows():
            country = str(row.get("Country", "")).strip()
            if not country or country.lower() == "nan":
                continue
            indices: dict[str, float] = {}
            for col in cols:
                if col in ("Rank", "Country"):
                    continue
                val = _clean_number(row.get(col))
                if val is not None:
                    indices[col] = val
            out[country] = indices
        break
    return out
