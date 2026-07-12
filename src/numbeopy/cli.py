"""numbeopy — command-line interface.

Usage:
    numbeopy list-countries [--currency USD]
    numbeopy fetch <country> [--currency USD] [--rate-limit 3.0]
                             [--no-country-indices] [--output PATH]

Examples:
    numbeopy fetch Turkey --output turkey.json
    numbeopy fetch "United States" --currency USD > usa.json
    numbeopy list-countries | head -20
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from numbeopy import __version__
from numbeopy.client import Client, DEFAULT_RATE_LIMIT_SECONDS, DEFAULT_USER_AGENT


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="numbeopy", description="Fetch Numbeo cost-of-living data.")
    p.add_argument("--version", action="version", version=f"numbeopy {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # list-countries
    lc = sub.add_parser("list-countries", help="List all countries on Numbeo rankings page")
    lc.add_argument("--currency", default="USD", help="Display currency (default: USD)")
    lc.add_argument("--rate-limit", type=float, default=DEFAULT_RATE_LIMIT_SECONDS,
                    help=f"Seconds between HTTP requests (default: {DEFAULT_RATE_LIMIT_SECONDS})")

    # fetch
    fc = sub.add_parser("fetch", help="Fetch full country snapshot")
    fc.add_argument("country", help="Country name (e.g. Turkey, Spain, 'United States')")
    fc.add_argument("--currency", default="USD", help="Display currency (default: USD)")
    fc.add_argument("--rate-limit", type=float, default=DEFAULT_RATE_LIMIT_SECONDS,
                    help=f"Seconds between HTTP requests (default: {DEFAULT_RATE_LIMIT_SECONDS})")
    fc.add_argument("--no-country-indices", action="store_true",
                    help="Skip the rankings-page fetch that populates country-level indices")
    fc.add_argument("--output", "-o", help="Write JSON to PATH (default: stdout)")

    return p


def cmd_list_countries(args) -> int:
    client = Client(rate_limit_seconds=args.rate_limit)
    for name in client.list_countries(currency=args.currency):
        print(name)
    return 0


def cmd_fetch(args) -> int:
    client = Client(rate_limit_seconds=args.rate_limit)
    data = client.fetch_country(
        country=args.country,
        currency=args.currency,
        include_country_indices=not args.no_country_indices,
    )
    payload = json.dumps(data.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"wrote {args.output} ({len(data.prices)} prices, {len(data.cities)} cities, "
              f"{len(data.indices)} country indices)", file=sys.stderr)
    else:
        print(payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list-countries":
        return cmd_list_countries(args)
    if args.command == "fetch":
        return cmd_fetch(args)
    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable


if __name__ == "__main__":
    sys.exit(main())
