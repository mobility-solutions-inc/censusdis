# Copyright (c) 2023 Darren Erik Vengroff
"""Tests for the fetch implementation."""

import unittest
from unittest.mock import Mock, call, patch

import pandas as pd
import requests

import censusdis.impl.fetch
from censusdis import CensusApiException


class ParseCensusJsonTestCase(unittest.TestCase):
    """Tests of parsing census JSON."""

    def test_parse_json(self):
        """Test parsing JSON."""
        # This is an example of what comes back in JSON
        # form from the census API.
        parsed_json = [
            ["B01001_001E", "state", "county", "tract"],
            ["1959", "01", "001", "020200"],
            ["2527", "01", "001", "021000"],
        ]

        # This is what we should turn that into. Note the
        # use of the header row for column names and that we
        # capitalize them.
        expected_df = pd.DataFrame(
            [
                ["1959", "01", "001", "020200"],
                ["2527", "01", "001", "021000"],
            ],
            columns=["B01001_001E", "STATE", "COUNTY", "TRACT"],
        )

        df = censusdis.impl.fetch._df_from_census_json(parsed_json)

        self.assertTrue((df == expected_df).all().all())

    def test_parse_bad_json(self):
        """Test with malformed JSON."""
        with self.assertRaises(CensusApiException):
            censusdis.impl.fetch._df_from_census_json([])


class JsonFromUrlTestCase(unittest.TestCase):
    """Tests of responses from the Census API."""

    @patch("censusdis.impl.fetch.sleep")
    @patch("censusdis.impl.fetch.requests.get")
    def test_retries_connection_errors_with_exponential_backoff(
        self, requests_get, sleep
    ):
        """Retry transient connection errors before returning JSON."""
        response = Mock(status_code=200)
        response.json.return_value = {"variables": {}}
        requests_get.side_effect = [
            requests.exceptions.ConnectionError("first failure"),
            requests.exceptions.ConnectionError("second failure"),
            requests.exceptions.ConnectionError("third failure"),
            response,
        ]

        actual_json = censusdis.impl.fetch.json_from_url(
            "https://api.census.gov/data/2023/acs/acs1/groups/B01001.json"
        )

        self.assertEqual({"variables": {}}, actual_json)
        self.assertEqual(4, requests_get.call_count)
        self.assertEqual(
            120,
            requests_get.call_args.kwargs["timeout"],
        )
        sleep.assert_has_calls([call(1), call(2), call(4)])

    @patch("censusdis.impl.fetch.requests.get")
    def test_current_invalid_api_key_response(self, requests_get):
        """Recognize the Census API's current invalid-key HTML response."""
        response = Mock()
        response.status_code = 200
        response.url = "https://api.census.gov/data/2023/acs/acs1"
        response.text = """
        <html>
          <head><title>Invalid Key</title></head>
          <body>A valid key must be included with this request.</body>
        </html>
        """
        response.json.side_effect = requests.exceptions.JSONDecodeError(
            "Expecting value", response.text, 0
        )
        requests_get.return_value = response

        with self.assertRaisesRegex(
            CensusApiException, "failed because your key is invalid"
        ):
            censusdis.impl.fetch.json_from_url(response.url)


if __name__ == "__main__":
    unittest.main()
