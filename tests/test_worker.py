"""Unit tests for the worker package (config, notifications, monitors).

These cover the pure business logic that was previously locked inside the
monolithic main.py: course-list parsing, notification dispatch/formatting,
grade-message rendering, and monitor selection.
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker import runner
from worker.config import _parse_courses
from worker.monitors.krs import KrsMonitor
from worker.monitors.nilai import GradeMonitor
from worker.notifications import Notifier


class DummyConfig:
    """Minimal config double for Notifier / monitor tests."""

    def __init__(self, **kw):
        self.telegram_token = kw.get("telegram_token")
        self.chat_id = kw.get("chat_id")
        self.waha_base_url = kw.get("waha_base_url")
        self.waha_session = kw.get("waha_session", "default")
        self.waha_api_key = kw.get("waha_api_key")
        self.whatsapp_number = kw.get("whatsapp_number")
        self.monitor_type = kw.get("monitor_type", "nilai")
        self.target_courses = kw.get("target_courses", [])


class FakeResp:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


class TestParseCourses:
    def test_valid_json_list(self):
        assert _parse_courses('["A", "B"]') == ["A", "B"]

    def test_empty_returns_empty_list(self):
        assert _parse_courses("") == []
        assert _parse_courses(None) == []

    def test_malformed_returns_empty_list(self):
        assert _parse_courses("{not json") == []
        assert _parse_courses("[1, 2,") == []


class TestNotifier:
    def test_telegram_skipped_without_credentials(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "worker.notifications.requests.post",
            lambda *a, **k: calls.append(1) or FakeResp(),
        )
        Notifier(DummyConfig()).telegram("hi")
        assert calls == []

    def test_telegram_posts_with_markdown(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, timeout=None, **k):
            captured["url"] = url
            captured["json"] = json
            return FakeResp(200)

        monkeypatch.setattr("worker.notifications.requests.post", fake_post)
        Notifier(DummyConfig(telegram_token="T", chat_id="123")).telegram("hello")
        assert "botT/sendMessage" in captured["url"]
        assert captured["json"]["parse_mode"] == "Markdown"
        assert captured["json"]["chat_id"] == "123"

    def test_waha_sanitizes_number_and_link(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None, **k):
            captured["json"] = json
            return FakeResp(201)

        monkeypatch.setattr("worker.notifications.requests.post", fake_post)
        cfg = DummyConfig(waha_base_url="http://waha", whatsapp_number="62812-345")
        Notifier(cfg).waha("[link](http://x)")
        assert captured["json"]["chatId"] == "62812345@c.us"
        assert captured["json"]["text"] == "link (http://x)"

    def test_send_dispatches_to_both_channels(self, monkeypatch):
        sent = []
        monkeypatch.setattr(Notifier, "telegram", lambda self, m: sent.append(("tg", m)))
        monkeypatch.setattr(Notifier, "waha", lambda self, m: sent.append(("wa", m)))
        cfg = DummyConfig(
            telegram_token="T", chat_id="1",
            waha_base_url="http://waha", whatsapp_number="628",
        )
        Notifier(cfg).send("msg")
        assert ("tg", "msg") in sent
        assert ("wa", "msg") in sent


class TestGradeMessage:
    def test_contains_course_grade_and_semester(self):
        monitor = GradeMonitor(DummyConfig(), notifier=None, session=object())
        monitor.selected_semester_title = "Ganjil 2025"
        msg = monitor._grade_message({"matkul": "Kalkulus", "nilai": "A", "mutu": "4.00"})
        assert "Kalkulus" in msg
        assert "`A`" in msg
        assert "Ganjil 2025" in msg


class TestBuildMonitor:
    def test_build_monitor_grades(self, monkeypatch):
        monkeypatch.setattr(runner.config, "monitor_type", "nilai")
        assert isinstance(runner.build_monitor(), GradeMonitor)

    def test_build_monitor_krs(self, monkeypatch):
        monkeypatch.setattr(runner.config, "monitor_type", "krs")
        assert isinstance(runner.build_monitor(), KrsMonitor)


class TestGradeLoopFirstRun:
    """Regression: grades appearing from an empty baseline must notify."""

    def _sample(self):
        return {
            "nama": "Mahasiswa", "nim": "123", "ips": "-", "ipk": "-", "total_sks": 23,
            "nilai": [
                {"matkul": "Sistem Terdistribusi", "sks": 2, "nilai": "95.8", "mutu": "A"},
                {"matkul": "Interaksi Manusia & Komputer", "sks": 3, "nilai": "---", "mutu": "---"},
                {"matkul": "Kewarganegaraan", "sks": 2, "nilai": "88.6", "mutu": "A"},
                {"matkul": "Analitika Data", "sks": 2, "nilai": "---", "mutu": "---"},
            ],
        }

    def _monitor(self, tmp_path, monkeypatch, sent):
        cfg = DummyConfig()
        cfg.file_data = str(tmp_path / "last_values.json")
        cfg.interval = 1
        notifier = types.SimpleNamespace(send=lambda msg: sent.append(msg))
        monitor = GradeMonitor(cfg, notifier, session=object())
        monkeypatch.setattr(monitor, "fetch", lambda: self._sample())
        return monitor, cfg

    def test_first_run_notifies_present_grades(self, tmp_path, monkeypatch):
        sent = []
        monitor, cfg = self._monitor(tmp_path, monkeypatch, sent)
        assert not os.path.exists(cfg.file_data)
        monitor.loop(run_once=True)
        assert len(sent) == 2
        assert any("Sistem Terdistribusi" in m for m in sent)
        assert any("Kewarganegaraan" in m for m in sent)
        assert os.path.exists(cfg.file_data)

    def test_second_run_does_not_renotify(self, tmp_path, monkeypatch):
        sent = []
        monitor, cfg = self._monitor(tmp_path, monkeypatch, sent)
        monitor.loop(run_once=True)
        sent.clear()
        monitor.loop(run_once=True)
        assert sent == []
