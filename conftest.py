"""Shared pytest configuration for tests that use the Census API."""

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import requests

_CENSUS_API_HOST = "api.census.gov"
_MISSING_KEY_PATH = "/data/missing_key.html"
_MISSING_KEY_TITLE = b"<title>Missing Key</title>"
_MISSING_KEY_SKIP_REASON = (
    "The Census API now requires US_CENSUS_API_KEY for live data queries."
)


def _census_api_key_available() -> bool:
    """Return whether pytest or a notebook kernel can load a Census API key."""
    key_file = Path.home() / ".censusdis" / "api_key.txt"
    return bool(os.environ.get("US_CENSUS_API_KEY")) or key_file.is_file()


def _is_missing_census_api_key_response(response: requests.Response) -> bool:
    """Return whether Census redirected a request to its missing-key page."""
    parsed_url = urlparse(response.url)
    return parsed_url.hostname == _CENSUS_API_HOST and (
        parsed_url.path == _MISSING_KEY_PATH or _MISSING_KEY_TITLE in response.content
    )


@pytest.fixture(autouse=True)
def skip_census_api_queries_without_key(
    monkeypatch: pytest.MonkeyPatch,
):
    """Skip a test when Census rejects its live query for lacking an API key."""
    original_request = requests.sessions.Session.request

    def request_or_skip(
        session: requests.Session,
        method: str,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> requests.Response:
        response = original_request(session, method, url, *args, **kwargs)
        if _is_missing_census_api_key_response(response):
            pytest.skip(_MISSING_KEY_SKIP_REASON)
        return response

    monkeypatch.setattr(requests.sessions.Session, "request", request_or_skip)
    yield


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip notebook execution when its kernel cannot receive a Census API key."""
    if _census_api_key_available():
        return

    skip_missing_key = pytest.mark.skip(reason=_MISSING_KEY_SKIP_REASON)
    for item in items:
        if item.path.suffix == ".ipynb":
            item.add_marker(skip_missing_key)
