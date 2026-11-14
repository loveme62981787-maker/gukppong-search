import io
import json
import unittest

import license_watch as lw


class ApiLicenseTests(unittest.TestCase):
    def fetch(self, items):
        def opener(url, timeout):
            return io.StringIO(json.dumps({"items": items}))
        return lw.fetch_api_license("abcdefghijk", "test-key", opener)

    def test_explicit_license_and_date(self):
        result = self.fetch([{"id": "abcdefghijk", "status": {"license": "creativeCommon"},
                             "snippet": {"publishedAt": "2025-01-01T20:00:00Z"}}])
        self.assertEqual(result[0], "ok")
        self.assertEqual(result[1]["license"], "cc_by")
        self.assertEqual(result[1]["published"], "2025-01-02")
        self.assertFalse(result[1]["has_desc"])

    def test_standard_and_missing_marker(self):
        self.assertEqual(self.fetch([{"id": "abcdefghijk", "status": {"license": "youtube"}}])[1]["license"], "standard")
        self.assertEqual(self.fetch([{"id": "abcdefghijk"}])[0], "err")

    def test_wrong_video_and_unavailable(self):
        self.assertEqual(self.fetch([{"id": "other-video"}]), ("err", "identity_mismatch"))
        self.assertEqual(self.fetch([]), ("err", "unavailable"))

    def test_error_preserves_previous_confirmation(self):
        def fail(url, timeout):
            raise OSError(url)
        result = lw.fetch_api_license("abcdefghijk", "test-key", fail)
        self.assertEqual(result, ("err", "http_error"))
        record = lw.observe({"license": "cc_by", "checked_at": "2026-11-01"}, result, lw.now_utc())
        self.assertEqual(record["license"], "cc_by")
        self.assertEqual(record["checked_at"], "2026-11-01")


class ApiSearchTests(unittest.TestCase):
    def test_search_filter_details_and_identity(self):
        import cc_discover as cc
        from urllib.parse import urlparse, parse_qs
        responses = [
            {"items": [{"id": {"videoId": "abcdefghijk"}}]},
            {"items": [{"id": "abcdefghijk", "snippet": {"title": "Taiwan travel vlog", "channelTitle": "Traveler", "channelId": "UC1"},
                        "contentDetails": {"duration": "PT1H2M3S"}, "statistics": {"viewCount": "123"}},
                       {"id": "wrong-id", "contentDetails": {"duration": "PT9M"}}]}]
        calls = []
        def opener(url, timeout):
            calls.append(parse_qs(urlparse(url).query))
            return io.StringIO(json.dumps(responses.pop(0)))
        found = cc.search_cc_api("Taiwan travel", "test-key", opener)
        self.assertEqual(calls[0]["videoLicense"], ["creativeCommon"])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["duration_sec"], 3723)
        self.assertEqual(found[0]["views"], 123)
        self.assertNotIn("status", found[0])

    def test_search_failure_does_not_expose_key(self):
        import cc_discover as cc
        def fail(url, timeout):
            raise OSError(url)
        with self.assertRaises(RuntimeError) as caught:
            cc.search_cc_api("Taiwan travel", "secret-value", fail)
        self.assertNotIn("secret-value", str(caught.exception))
