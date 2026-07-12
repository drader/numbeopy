"""numbeopy — command-line interface.

Usage:
    numbeopy list-countries [--currency USD]
    numbeopy fetch <country> [--currency USD] [--all]
    numbeopy fetch-city <country> <city> [--currency USD]
    numbeopy rankings quality-of-life
    numbeopy rankings property [--by-city]
    numbeopy rankings crime
    numbeopy rankings health-care
    numbeopy rankings pollution
    numbeopy rankings traffic

Examples:
    numbeopy fetch Turkey --all --output turkey-full.json
    numbeopy fetch-city Turkey Istanbul --output istanbul.json
    numbeopy rankings quality-of-life > qol.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from numbeopy import __version__
from numbeopy.client import Client, DEFAULT_RATE_LIMIT_SECONDS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="numbeopy", description="Fetch Numbeo cost-of-living data.")
    p.add_argument("--version", action="version", version=f"numbeopy {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    common_rate = dict(type=float, default=DEFAULT_RATE_LIMIT_SECONDS,
                       help=f"Seconds between HTTP requests (default: {DEFAULT_RATE_LIMIT_SECONDS})")

    # list-countries
    lc = sub.add_parser("list-countries", help="List all countries on Numbeo rankings page")
    lc.add_argument("--currency", default="USD")
    lc.add_argument("--rate-limit", **common_rate)

    # fetch (country)
    fc = sub.add_parser("fetch", help="Fetch a country snapshot (cost-of-living page)")
    fc.add_argument("country")
    fc.add_argument("--currency", default="USD")
    fc.add_argument("--rate-limit", **common_rate)
    fc.add_argument("--no-country-indices", action="store_true")
    fc.add_argument("--all", "--all-categories", action="store_true", dest="all_categories",
                    help="Also fetch QoL, property, crime, health, pollution, traffic (7 HTTP calls total)")
    fc.add_argument("--output", "-o")

    # fetch-city
    fci = sub.add_parser("fetch-city", help="Fetch prices for one specific city")
    fci.add_argument("country")
    fci.add_argument("city")
    fci.add_argument("--currency", default="USD")
    fci.add_argument("--rate-limit", **common_rate)
    fci.add_argument("--output", "-o")

    # rankings
    r = sub.add_parser("rankings", help="Fetch a category-level rankings page")
    r.add_argument("category", choices=[
        "quality-of-life", "property", "crime",
        "health-care", "pollution", "traffic",
    ])
    r.add_argument("--by-city", action="store_true",
                   help="For 'property' only: city-level rather than country-level rankings")
    r.add_argument("--rate-limit", **common_rate)
    r.add_argument("--output", "-o")

    return p


def _emit(payload, output_path: str | None, msg: str) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=_default)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        print(f"wrote {output_path} ({msg})", file=sys.stderr)
    else:
        print(text)


def _default(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    raise TypeError(f"non-serializable: {type(obj).__name__}")


def cmd_list_countries(args) -> int:
    client = Client(rate_limit_seconds=args.rate_limit)
    for name in client.list_countries(currency=args.currency):
        print(name)
    return 0


def cmd_fetch(args) -> int:
    client = Client(rate_limit_seconds=args.rate_limit)
    data = client.fetch_country(
        country=args.country, currency=args.currency,
        include_country_indices=not args.no_country_indices,
        include_all_categories=args.all_categories,
    )
    extras = ""
    if args.all_categories:
        extras = ", +6 category indices"
    _emit(data.to_dict(), args.output,
          f"{len(data.prices)} prices, {len(data.cities)} cities, "
          f"{len(data.indices)} COL indices{extras}")
    return 0


def cmd_fetch_city(args) -> int:
    client = Client(rate_limit_seconds=args.rate_limit)
    data = client.fetch_city(country=args.country, city=args.city, currency=args.currency)
    _emit(data.to_dict(), args.output,
          f"{len(data.prices)} prices for {args.city}, {args.country}")
    return 0


def cmd_rankings(args) -> int:
    client = Client(rate_limit_seconds=args.rate_limit)
    result: dict = {}
    if args.category == "quality-of-life":
        result = client.quality_of_life_rankings()
    elif args.category == "property":
        result = (client.property_rankings_by_city()
                  if args.by_city else client.property_rankings_by_country())
    elif args.category == "crime":
        result = client.crime_rankings()
    elif args.category == "health-care":
        result = client.health_care_rankings()
    elif args.category == "pollution":
        result = client.pollution_rankings()
    elif args.category == "traffic":
        result = client.traffic_rankings()
    scope = "cities" if (args.category == "property" and args.by_city) else "countries"
    _emit(result, args.output, f"{len(result)} {scope}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list-countries":
        return cmd_list_countries(args)
    if args.command == "fetch":
        return cmd_fetch(args)
    if args.command == "fetch-city":
        return cmd_fetch_city(args)
    if args.command == "rankings":
        return cmd_rankings(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
