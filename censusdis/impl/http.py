"""HTTP downloads that reject Brotli before response bodies are decoded."""

from typing import Any

import requests


def _reject_brotli(response: requests.Response, **kwargs: Any) -> requests.Response:
    """Reject Brotli in responses, including redirect and error bodies."""
    encodings = response.headers.get("Content-Encoding", "").split(",")
    if any(encoding.strip().lower() == "br" for encoding in encodings):
        response.close()
        raise requests.exceptions.ContentDecodingError(
            "Brotli HTTP responses are disabled due to CVE-2026-111497.",
            response=response,
        )
    return response


def get(url: str, **kwargs: Any) -> requests.Response:
    """Download without Brotli, checking headers before Requests reads any body."""
    # A response hook also runs before Requests consumes redirect bodies.
    # Accept-Encoding alone cannot stop a server from sending Brotli anyway.
    return requests.get(
        url,
        headers={"Accept-Encoding": "gzip, deflate"},
        hooks={"response": _reject_brotli},
        **kwargs,
    )
