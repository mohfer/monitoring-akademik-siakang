"""Unit Tests untuk Scraper Library (Playwright-based).

Sejak migrasi ke Playwright, scraper memakai BrowserSession (Chromium) alih-alih
requests.Session. Test ini mem_mock_ method BrowserSession agar tidak meluncurkan
browser sungguhan, sambil tetap menguji logika parsing semester yang nyata.

Tests cover:
- SiakangScraper initialization
- Login (success / wrong credentials / error) via BrowserSession
- Semester parsing (success / empty / HTTP error)
- Resp adapter helper
- IPv4 socket enforcement
"""

import pytest
import sys
import os
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper_lib import SiakangScraper, BrowserSession, Resp


@pytest.fixture
def scraper():
    """Create a scraper instance with test credentials."""
    return SiakangScraper("test123", "password123")


def make_resp(text="", url="https://siakang.untirta.ac.id", status_code=200):
    return Resp(text=text, url=url, status_code=status_code)


class TestScraperInit:
    """Tests for scraper initialization."""

    def test_scraper_creation(self, scraper):
        """Test that scraper is created with correct attributes."""
        assert scraper.login_id == "test123"
        assert scraper.password == "password123"
        assert isinstance(scraper.session, BrowserSession)

    def test_scraper_headers(self, scraper):
        """Test that the underlying session exposes a User-Agent header."""
        assert "User-Agent" in scraper.session.headers


class TestRespAdapter:
    """Tests for the requests-like Resp adapter."""

    def test_ok_property(self):
        assert make_resp(status_code=200).ok is True
        assert make_resp(status_code=302).ok is True
        assert make_resp(status_code=404).ok is False

    def test_json_parsing(self):
        resp = make_resp(text='{"a": 1, "b": [2, 3]}')
        assert resp.json() == {"a": 1, "b": [2, 3]}


class TestScraperLogin:
    """Tests for login functionality (BrowserSession mocked)."""

    def test_login_success(self, scraper):
        """Test successful login delegates to the session and keeps it open."""
        scraper.session = MagicMock(spec=BrowserSession)
        scraper.session.login.return_value = (True, "Success")

        success, msg = scraper.login()

        assert success is True
        assert msg == "Success"
        scraper.session.login.assert_called_once_with("test123", "password123")
        scraper.session.close.assert_not_called()

    def test_login_wrong_credentials(self, scraper):
        """Test login with wrong credentials closes the browser."""
        scraper.session = MagicMock(spec=BrowserSession)
        scraper.session.login.return_value = (False, "Identitas Salah")

        success, msg = scraper.login()

        assert success is False
        assert "Salah" in msg
        scraper.session.close.assert_called_once()

    def test_login_network_error(self, scraper):
        """Test login surfaces error messages from the session."""
        scraper.session = MagicMock(spec=BrowserSession)
        scraper.session.login.return_value = (False, "Network error")

        success, msg = scraper.login()

        assert success is False
        assert "Network error" in msg


class TestScraperSemesters:
    """Tests for semester parsing (BrowserSession.get mocked)."""

    def test_get_semesters_success(self, scraper):
        """Test successful semester parsing from HTML."""
        html = """
        <div class="col-12 col-md-6 col-lg-4">
            <h5 class="card-title">Semester Ganjil 2024</h5>
            <p class="card-text">Kode Semester #20241</p>
            <a class="btn-primary" href="/semester/20241">Select</a>
        </div>
        """
        scraper.session = MagicMock(spec=BrowserSession)
        scraper.session.get.return_value = make_resp(text=html, status_code=200)

        semesters = scraper.get_semesters()

        assert len(semesters) == 1
        assert semesters[0]["title"] == "Semester Ganjil 2024"
        assert semesters[0]["code"] == "20241"
        assert semesters[0]["url"] == "/semester/20241"
        scraper.session.close.assert_called_once()

    def test_get_semesters_empty(self, scraper):
        """Test when no semester cards are present."""
        scraper.session = MagicMock(spec=BrowserSession)
        scraper.session.get.return_value = make_resp(
            text="<html><body></body></html>", status_code=200
        )

        semesters = scraper.get_semesters()

        assert len(semesters) == 0

    def test_get_semesters_error(self, scraper):
        """Test semester fetching when server returns non-200."""
        scraper.session = MagicMock(spec=BrowserSession)
        scraper.session.get.return_value = make_resp(text="", status_code=500)

        semesters = scraper.get_semesters()

        assert len(semesters) == 0

    def test_get_semesters_closes_on_exception(self, scraper):
        """Browser must be closed even if parsing raises."""
        scraper.session = MagicMock(spec=BrowserSession)
        scraper.session.get.side_effect = Exception("boom")

        with pytest.raises(Exception):
            scraper.get_semesters()

        scraper.session.close.assert_called_once()


class TestIPv4Enforcement:
    """Tests for IPv4 enforcement."""

    def test_socket_patched(self):
        """Test that socket.getaddrinfo is patched for IPv4."""
        import socket
        import scraper_lib  # noqa: F401  (imports and patches socket)

        assert socket.getaddrinfo is scraper_lib.getaddrinfo_ipv4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
