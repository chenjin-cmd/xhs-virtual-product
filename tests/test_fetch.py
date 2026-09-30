"""离线合成样本，不含真实账号、凭据或平台请求。"""
import importlib
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PROFILE_ID = "a" * 24
NOTE_ID = "b" * 24
JPEG = b"\xff\xd8\xff" + b"synthetic-image"


def html_for(state):
    return '<script>window.__INITIAL_STATE__ = ' + json.dumps(state) + ';</script>'


def profile_state():
    return {"profile": {
        "userInfo": {"nickname": "合成样本", "fans": "1.2万", "follows": 0},
        "noteCollectionList": [],
        "noteData": [{"id": "c" * 32, "title": "合成表格笔记", "likes": "1,234",
                      "collects": 0, "cover": {"url": "https://images.example.invalid/cover.jpg"}}],
    }}


def note_state():
    return {"noteData": {"data": {"noteData": {
        "noteId": NOTE_ID, "title": "合成笔记", "desc": "自己的使用说明",
        "user": {}, "tagList": [], "interactInfo": {"collectedCount": "120"},
        "imageList": [{"url": "https://images.example.invalid/page.jpg", "width": 900, "height": 1200}],
    }}}}


class CollectorTests(unittest.TestCase):
    def setUp(self):
        streams = contextlib.ExitStack()
        streams.enter_context(contextlib.redirect_stdout(io.StringIO()))
        streams.enter_context(contextlib.redirect_stderr(io.StringIO()))
        self.addCleanup(streams.close)

    @classmethod
    def setUpClass(cls):
        cls.common = importlib.import_module("xhs_common")
        cls.profile = importlib.import_module("fetch_profile")
        cls.note = importlib.import_module("fetch_note")

    def test_state_preserves_undefined_inside_text(self):
        html = '<script>window.__INITIAL_STATE__ = {"text":"undefined", "missing":undefined};</script>'
        self.assertEqual(self.common.parse_state(html), {"text": "undefined", "missing": None})

    def test_state_rejects_missing_or_broken_payload(self):
        for html in ("<html>blocked</html>", '<script>__INITIAL_STATE__={broken}</script>'):
            with self.subTest(html=html), self.assertRaises(self.common.CollectionError):
                self.common.parse_state(html)

    def test_numbers_preserve_missing_and_precision(self):
        cases = [("1,234", 1234, "exact"), ("1.2万", 12000, "approximate"),
                 ("2万+", 20000, "lower_bound"), (0, 0, "exact"),
                 (None, None, "unknown"), ("--", None, "unknown")]
        for raw, value, precision in cases:
            with self.subTest(raw=raw):
                result = self.common.normalize_count(raw)
                self.assertEqual(result, {"raw": raw, "value": value, "precision": precision})

    def test_targets_validate_host_id_and_token(self):
        uid, url = self.common.parse_target(PROFILE_ID, "profile")
        self.assertEqual(uid, PROFILE_ID)
        self.assertEqual(url, "https://www.xiaohongshu.com/user/profile/" + PROFILE_ID)
        _, url = self.common.parse_target(
            "https://www.xiaohongshu.com/explore/" + NOTE_ID + "?xsec_token=a%26b&xsec_source=pc_user", "note")
        self.assertIn("xsec_token=a%26b", url)
        for target, kind in [("bad-id", "profile"),
                             ("https://evil.invalid/user/profile/" + PROFILE_ID, "profile"),
                             ("https://www.xiaohongshu.com/explore/" + NOTE_ID, "note")]:
            with self.subTest(target=target), self.assertRaises(self.common.CollectionError):
                self.common.parse_target(target, kind)

    def test_output_requires_outside_repository(self):
        with self.assertRaises(self.common.CollectionError):
            self.common.prepare_output(ROOT / "output" / "synthetic")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.common.prepare_output(Path(tmp) / "work"), (Path(tmp) / "work").resolve())

    def test_http_failure_is_one_attempt_and_redacts_token(self):
        failed = subprocess.CompletedProcess([], 22, stdout=b"", stderr=b"secret-token")
        with patch("xhs_common.subprocess.run", return_value=failed) as run:
            with self.assertRaises(self.common.CollectionError) as caught:
                self.common.RequestClient().fetch_html("https://example.invalid/?xsec_token=secret-token")
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("secret-token", str(caught.exception))

    def test_request_spacing_includes_page_and_download(self):
        clock = [10.0]
        def advance(seconds):
            clock[0] += seconds
        with patch("xhs_common.time.monotonic", side_effect=lambda: clock[0]), \
             patch("xhs_common.time.sleep", side_effect=advance) as sleep, \
             patch("xhs_common.subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"ok", b"")):
            client = self.common.RequestClient(interval=1.5)
            client.fetch_html("https://example.invalid/page")
            client.fetch_html("https://example.invalid/page2")
        self.assertEqual(sleep.call_args.args[0], 1.5)

    def test_image_failure_does_not_leave_old_or_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "cover.jpg"
            destination.write_bytes(JPEG)
            def fake_run(command, **kwargs):
                Path(command[command.index("--output") + 1]).write_bytes(b"<html>blocked</html>")
                return subprocess.CompletedProcess(command, 0, b"", b"")
            with patch("xhs_common.subprocess.run", side_effect=fake_run):
                result = self.common.RequestClient().download("https://example.invalid/image", destination)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(destination.exists())
            self.assertFalse(list(Path(tmp).glob("*.part")))

    def test_image_success_checks_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "cover.jpg"
            def fake_run(command, **kwargs):
                Path(command[command.index("--output") + 1]).write_bytes(JPEG)
                return subprocess.CompletedProcess(command, 0, b"", b"")
            with patch("xhs_common.subprocess.run", side_effect=fake_run):
                result = self.common.RequestClient().download("https://example.invalid/image", destination)
            self.assertEqual(result["status"], "downloaded")
            self.assertEqual(destination.read_bytes(), JPEG)

    def test_download_failure_stops_remaining_requests(self):
        items = [{"destination": "img{}.jpg".format(i), "download_url": "https://example.invalid/image"}
                 for i in (1, 2, 3)]
        client = self.common.RequestClient()
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(client, "download", return_value={"status": "failed", "error": "blocked"}) as download:
            self.common.download_images(client, items, Path(tmp), "file")
        self.assertEqual(download.call_count, 1)
        self.assertEqual([item["download"]["status"] for item in items], ["failed", "skipped", "skipped"])

    def test_interval_rejects_zero_nan_and_infinite(self):
        for interval in (0, -1, float("nan"), float("inf")):
            with self.subTest(interval=interval), self.assertRaises(self.common.CollectionError):
                self.common.RequestClient(interval)

    def test_profile_records_scope_raw_counts_and_missing_values(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch("xhs_common.RequestClient.fetch_html", return_value=html_for(profile_state())), \
             patch("xhs_common.RequestClient.download", return_value={"status": "failed", "error": "synthetic failure"}):
            code = self.profile.main([PROFILE_ID, "-o", tmp])
            self.assertEqual(code, 2)
            profile = json.loads((Path(tmp) / "profile.json").read_text())
            notes = json.loads((Path(tmp) / "notes_list.json").read_text())
            manifest = json.loads((Path(tmp) / "manifest.json").read_text())
            self.assertEqual(profile["fans"], "1.2万")
            self.assertEqual(profile["metrics"]["fans"]["precision"], "approximate")
            self.assertIsNone(profile["metrics"]["like_and_collect"]["value"])
            self.assertEqual(notes[0]["collects"], 0)
            self.assertIn("collects_zero_unverified", notes[0]["warnings"])
            self.assertIsNone(notes[0]["cover_file"])
            self.assertEqual(manifest["sample_count"], 1)
            self.assertTrue(manifest["collected_at"].endswith("Z"))

    def test_note_retains_image_index_and_omits_token(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch("xhs_common.RequestClient.fetch_html", return_value=html_for(note_state())), \
             patch("xhs_common.RequestClient.download", return_value={"status": "failed", "error": "synthetic failure"}):
            code = self.note.main(["https://www.xiaohongshu.com/explore/" + NOTE_ID + "?xsec_token=synthetic-secret", "-o", tmp])
            self.assertEqual(code, 2)
            meta = json.loads((Path(tmp) / "meta.json").read_text())
            images = json.loads((Path(tmp) / "images.json").read_text())
            self.assertEqual(meta["metrics"]["collectedCount"]["value"], 120)
            self.assertEqual(images[0]["idx"], 1)
            self.assertIsNone(images[0]["file"])
            for file in Path(tmp).iterdir():
                self.assertNotIn("synthetic-secret", file.read_text())

    def test_mismatched_note_does_not_write_report_data(self):
        state = note_state()
        state["noteData"]["data"]["noteData"]["noteId"] = "d" * 24
        with tempfile.TemporaryDirectory() as tmp, \
             patch("xhs_common.RequestClient.fetch_html", return_value=html_for(state)):
            code = self.note.main(["https://www.xiaohongshu.com/explore/" + NOTE_ID + "?xsec_token=synthetic", "-o", tmp])
            self.assertEqual(code, 1)
            self.assertFalse((Path(tmp) / "meta.json").exists())
            self.assertEqual(json.loads((Path(tmp) / "manifest.json").read_text())["status"], "failed")

    def test_rerun_failure_invalidates_stale_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "profile.json").write_text('{"nickname":"old"}')
            with patch("xhs_common.RequestClient.fetch_html", side_effect=self.common.CollectionError("blocked")):
                self.assertEqual(self.profile.main([PROFILE_ID, "-o", tmp]), 1)
            self.assertFalse((Path(tmp) / "profile.json").exists())

    def test_changed_profile_schema_is_not_empty_success(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch("xhs_common.RequestClient.fetch_html", return_value=html_for({"profile": {"unrecognized": []}})):
            self.assertEqual(self.profile.main([PROFILE_ID, "-o", tmp]), 1)

    def test_malformed_optional_collection_returns_controlled_failure(self):
        state = profile_state()
        state["profile"]["noteCollectionList"] = 42
        with tempfile.TemporaryDirectory() as tmp, \
             patch("xhs_common.RequestClient.fetch_html", return_value=html_for(state)):
            self.assertEqual(self.profile.main([PROFILE_ID, "-o", tmp]), 1)

    def test_malformed_tag_list_returns_controlled_failure(self):
        state = note_state()
        state["noteData"]["data"]["noteData"]["tagList"] = 42
        with tempfile.TemporaryDirectory() as tmp, \
             patch("xhs_common.RequestClient.fetch_html", return_value=html_for(state)):
            self.assertEqual(self.note.main(["https://www.xiaohongshu.com/explore/" + NOTE_ID + "?xsec_token=synthetic", "-o", tmp]), 1)

    def test_malformed_image_url_is_recorded_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.common.RequestClient().download("https://[invalid/image", Path(tmp) / "image.jpg")
            self.assertEqual(result["status"], "failed")

    def test_complete_collection_through_curl_boundary(self):
        for script, target, state, data_file, image_file in [
            (self.profile, PROFILE_ID, profile_state(), "profile.json", "covers/cover1.jpg"),
            (self.note, "https://www.xiaohongshu.com/explore/" + NOTE_ID + "?xsec_token=synthetic", note_state(), "meta.json", "img1.jpg"),
        ]:
            def fake_curl(command, **kwargs):
                if "--output" in command:
                    Path(command[command.index("--output") + 1]).write_bytes(JPEG)
                    return subprocess.CompletedProcess(command, 0, b"", b"")
                return subprocess.CompletedProcess(command, 0, html_for(state).encode(), b"")
            with self.subTest(script=script.__name__), tempfile.TemporaryDirectory() as tmp, \
                 patch("xhs_common.subprocess.run", side_effect=fake_curl), patch("xhs_common.time.sleep"):
                self.assertEqual(script.main([target, "-o", tmp]), 0)
                self.assertTrue((Path(tmp) / data_file).exists())
                self.assertEqual((Path(tmp) / image_file).read_bytes(), JPEG)
                manifest = json.loads((Path(tmp) / "manifest.json").read_text())
                self.assertEqual(manifest["status"], "complete")
                self.assertEqual(manifest["downloads"]["downloaded"], 1)

    def test_cli_missing_out_is_rejected_before_network(self):
        for script, target in [("fetch_profile.py", PROFILE_ID), ("fetch_note.py", "invalid")]:
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), target], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("--out", result.stderr)


if __name__ == "__main__":
    unittest.main()
