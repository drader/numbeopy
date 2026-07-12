"""Offline tests for numbeopy.Client using mocked HTTP session.

Verifies caching + rate-limit + provenance-stamping behavior without touching
the live network. This means these run in CI and never consume Numbeo request
budget.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from numbeopy import Client

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_session_returning(html: str) -> MagicMock:
    """Build a MagicMock requests.Session whose .get() always returns `html`."""
    session = MagicMock()
    response = MagicMock()
    response.text = html
    response.content = html.encode("utf-8")
    response.status_code = 200
    response.raise_for_status = MagicMock()
    session.get.return_value = response
    return session


def _load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestClientCaching:
    def test_qol_rankings_cached_per_instance(self) -> None:
        session = _fake_session_returning(_load_fixture("quality_of_life_rankings.html"))
        client = Client(session=session, rate_limit_seconds=0.0)

        first = client.quality_of_life_rankings()
        second = client.quality_of_life_rankings()

        assert first is second, "second call should return the same cached dict"
        assert session.get.call_count == 1, "network hit only on first call"

    def test_crime_rankings_cached_per_instance(self) -> None:
        session = _fake_session_returning(_load_fixture("crime_rankings.html"))
        client = Client(session=session, rate_limit_seconds=0.0)
        client.crime_rankings()
        client.crime_rankings()
        assert session.get.call_count == 1

    def test_different_ranking_methods_are_independent(self) -> None:
        # Return the appropriate fixture based on URL substring.
        qol = _load_fixture("quality_of_life_rankings.html")
        crime = _load_fixture("crime_rankings.html")

        def fake_get(url, *a, **kw):
            body = qol if "quality-of-life" in url else crime
            r = MagicMock()
            r.text = body
            r.content = body.encode("utf-8")
            r.status_code = 200
            r.raise_for_status = MagicMock()
            return r

        session = MagicMock()
        session.get.side_effect = fake_get
        client = Client(session=session, rate_limit_seconds=0.0)

        client.quality_of_life_rankings()
        client.crime_rankings()
        assert session.get.call_count == 2  # one per distinct category


class TestClientProvenance:
    def test_fetch_country_stamps_url_and_sha(self) -> None:
        session = _fake_session_returning(_load_fixture("country_result_turkey.html"))
        # Also need rankings to populate country_indices — return the rankings fixture
        # when that URL is called instead.
        rankings_html = _load_fixture("rankings_by_country_usd.html")
        country_html = _load_fixture("country_result_turkey.html")

        def fake_get(url, *a, **kw):
            body = rankings_html if "rankings_by_country" in url else country_html
            r = MagicMock()
            r.text = body
            r.content = body.encode("utf-8")
            r.status_code = 200
            r.raise_for_status = MagicMock()
            return r

        session = MagicMock()
        session.get.side_effect = fake_get
        client = Client(session=session, rate_limit_seconds=0.0)

        data = client.fetch_country(country="Turkey")
        assert data.source_url.startswith("https://www.numbeo.com/cost-of-living/country_result.jsp")
        assert "country=Turkey" in data.source_url
        assert len(data.source_sha256) == 64
        assert data.fetched_at         # ISO timestamp populated
