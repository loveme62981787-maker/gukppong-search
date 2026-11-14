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
