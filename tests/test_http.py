"""Test HTTP compression protection without contacting remote servers."""

import gzip
import zlib
from io import BytesIO
from unittest.mock import Mock

import pytest
import requests
from requests.structures import CaseInsensitiveDict
from urllib3.response import HTTPResponse

import censusdis.data as ced
import censusdis.geography as cgeo
import censusdis.maps as cmap
from censusdis.datasets import LODES_WAC_S000_JT05
from censusdis.impl.fetch import json_from_url
from censusdis.impl.http import get


def _response(status=200, headers=None, body=b""):
    """Create a response whose body has not been consumed or decoded."""
    response = requests.Response()
    response.status_code = status
    response.headers = CaseInsensitiveDict(headers or {})
    response.raw = HTTPResponse(
        body=BytesIO(body),
        headers=response.headers,
        preload_content=False,
        decode_content=False,
    )
    return response


def _serve(monkeypatch, responses):
    """Serve prepared responses through the real Requests response pipeline."""
    requests_seen = []
    responses = iter(responses)

    def send(adapter, request, **kwargs):
        requests_seen.append(request)
        response = next(responses)
        response.url = request.url
        response.request = request
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return requests_seen


@pytest.mark.parametrize(
    "encoding", ["br", "BR", "gzip, br", "br, gzip", " gzip , BR "]
)
@pytest.mark.parametrize("status", [200, 302, 500])
def test_reject_brotli_before_reading_any_body(monkeypatch, encoding, status):
    """Block Brotli before decompression, even on redirects and HTTP errors."""
    response = _response(
        status=status,
        headers={"Content-Encoding": encoding, "Location": "/redirected"},
        body=b"This body must never reach a decoder.",
    )
    read = Mock(side_effect=AssertionError("Response body was read"))
    response.raw.read = read
    requests_seen = _serve(monkeypatch, [response])

    with pytest.raises(
        requests.exceptions.ContentDecodingError, match="CVE-2026-111497"
    ) as exc:
        get("https://census.example/data")

    assert exc.value.response is response
    read.assert_not_called()
    assert response.raw.closed
    assert len(requests_seen) == 1
    assert requests_seen[0].headers["Accept-Encoding"] == "gzip, deflate"


@pytest.mark.parametrize("encoding", [None, "gzip", "deflate"])
def test_read_allowed_responses(monkeypatch, encoding):
    """Keep JSON downloads and normal HTTP compression decoding working."""
    body = b'{"variables": {}}'
    compress = {
        None: lambda data: data,
        "gzip": gzip.compress,
        "deflate": zlib.compress,
    }
    response = _response(
        headers={"Content-Encoding": encoding} if encoding else {},
        body=compress[encoding](body),
    )
    _serve(monkeypatch, [response])

    assert get("https://census.example/data").json() == {"variables": {}}


def test_reject_brotli_after_redirect(monkeypatch):
    """Retain the protection on requests made while following redirects."""
    redirect = _response(status=302, headers={"Location": "/redirected"})
    response = _response(headers={"Content-Encoding": "br"})
    read = Mock(side_effect=AssertionError("Response body was read"))
    response.raw.read = read
    requests_seen = _serve(monkeypatch, [redirect, response])

    with pytest.raises(requests.exceptions.ContentDecodingError):
        get("https://census.example/data")

    read.assert_not_called()
    assert response.raw.closed
    assert len(requests_seen) == 2
    assert requests_seen[1].headers["Accept-Encoding"] == "gzip, deflate"


def test_follow_gzip_redirect(monkeypatch):
    """Continue following redirects whose bodies use an allowed encoding."""
    redirect = _response(
        status=302,
        headers={"Location": "/redirected", "Content-Encoding": "gzip"},
        body=gzip.compress(b"Redirecting"),
    )
    response = _response(body=b"downloaded")
    requests_seen = _serve(monkeypatch, [redirect, response])

    result = get("https://census.example/data")

    assert result.content == b"downloaded"
    assert result.history[0].content == b"Redirecting"
    assert len(requests_seen) == 2


@pytest.mark.parametrize("download", ["json", "geography", "shapefile", "lodes"])
def test_census_downloads_use_compression_protection(monkeypatch, download):
    """Exercise the guard from each Census HTTP entry point."""
    response = _response(headers={"Content-Encoding": "br"})
    read = Mock(side_effect=AssertionError("Response body was read"))
    response.raw.read = read
    _serve(monkeypatch, [response])

    with pytest.raises(
        requests.exceptions.ContentDecodingError, match="CVE-2026-111497"
    ):
        if download == "json":
            json_from_url("https://census.example/data")
        elif download == "geography":
            cgeo.PathSpec._fetch_path_specs("acs/acs5", 2020)
        elif download == "shapefile":
            cmap._download_with_retries(
                "https://census.example/map.zip", timeout=120, cert=None, verify=True
            )
        else:
            ced.download_lodes(LODES_WAC_S000_JT05, 2020, state="34")

    read.assert_not_called()
    assert response.raw.closed
