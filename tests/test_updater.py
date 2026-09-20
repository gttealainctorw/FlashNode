"""Update check: version comparison, response validation, failure tolerance."""

import unittest
from unittest import mock

from tests.helpers import ROOT  # noqa: F401

from app import updater


class FakeResponse:
    def __init__(self, payload=None, status_ok=True, raise_json=False):
        self._payload = payload
        self._ok = status_ok
        self._raise_json = raise_json

    def raise_for_status(self):
        if not self._ok:
            raise updater.requests.HTTPError("503")

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


class VersionCompareTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(updater.parse_version("1.2.0"), (1, 2, 0))
        self.assertEqual(updater.parse_version(" 2 "), (2,))
        self.assertIsNone(updater.parse_version("v1.2"))
        self.assertIsNone(updater.parse_version("1.2.0-beta"))
        self.assertIsNone(updater.parse_version(None))
        self.assertIsNone(updater.parse_version(120))

    def test_is_newer(self):
        self.assertTrue(updater.is_newer("1.0.1", "1.0.0"))
        self.assertTrue(updater.is_newer("1.10.0", "1.9.9"))
        self.assertTrue(updater.is_newer("2", "1.9.9"))
        self.assertFalse(updater.is_newer("1.0.0", "1.0.0"))
        self.assertFalse(updater.is_newer("0.9.0", "1.0.0"))       # older remote is not an update
        self.assertFalse(updater.is_newer("garbage", "1.0.0"))


class CheckUpdateTest(unittest.TestCase):
    URL = "https://example.invalid/version.json"

    def check(self, response=None, exc=None, local="1.0.0"):
        with mock.patch.object(updater, "get_local_version", return_value=local), \
             mock.patch.object(updater.requests, "get", side_effect=exc, return_value=response):
            return updater.check_update(self.URL)

    def test_newer_version_available(self):
        self.assertEqual(self.check(FakeResponse({"version": "1.1.0"})), (True, "1.1.0"))

    def test_same_or_older_version(self):
        self.assertEqual(self.check(FakeResponse({"version": "1.0.0"})), (False, "1.0.0"))
        self.assertEqual(self.check(FakeResponse({"version": "0.5.0"})), (False, "0.5.0"))

    def test_network_problems_mean_no_update(self):
        self.assertEqual(self.check(exc=updater.requests.ConnectionError()), (False, None))
        self.assertEqual(self.check(exc=updater.requests.Timeout()), (False, None))
        self.assertEqual(self.check(FakeResponse(status_ok=False)), (False, None))

    def test_malformed_payloads(self):
        self.assertEqual(self.check(FakeResponse(raise_json=True)), (False, None))
        self.assertEqual(self.check(FakeResponse(["1.1.0"])), (False, None))
        self.assertEqual(self.check(FakeResponse({"version": "<script>"})), (False, None))
        self.assertEqual(self.check(FakeResponse({"nope": "1.1.0"})), (False, None))

    def test_disabled_or_insecure_url_never_hits_the_network(self):
        with mock.patch.object(updater.requests, "get") as get:
            self.assertEqual(updater.check_update(""), (False, None))
            self.assertEqual(updater.check_update("http://example.invalid/v.json"), (False, None))
            get.assert_not_called()

    def test_local_version_reads_bundled_file(self):
        self.assertIsNotNone(updater.parse_version(updater.get_local_version()))


if __name__ == "__main__":
    unittest.main()
