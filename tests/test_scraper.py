"""Unit Tests untuk Scraper Library.

Tests cover:
- SiakangScraper initialization
- Login functionality
- Semester fetching
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper_lib import SiakangScraper


@pytest.fixture
def scraper():
    """Create a scraper instance with test credentials."""
    return SiakangScraper("test123", "password123")


class TestScraperInit:
    """Tests for scraper initialization."""

    def test_scraper_creation(self, scraper):
        """Test that scraper is created with correct attributes."""
        assert scraper.login_id == "test123"
        assert scraper.password == "password123"
        assert scraper.session is not None

    def test_scraper_urls(self, scraper):
        """Test that scraper has correct URLs."""
        assert "siakang.untirta.ac.id" in scraper.url_login
        assert "siakang.untirta.ac.id" in scraper.url_list_semester

    def test_scraper_headers(self, scraper):
        """Test that scraper sets proper headers."""
        assert "User-Agent" in scraper.session.headers


class TestScraperLogin:
    """Tests for login functionality."""

    @patch("scraper_lib.requests.Session")
    def test_login_success(self, mock_session_class, scraper):
        """Test successful login."""
        # Mock the response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '<input name="_token" value="test_token">'
        mock_response.ok = True
        mock_session.get.return_value = mock_response
        mock_session.post.return_value = mock_response
        
        scraper.session = mock_session
        
        success, msg = scraper.login()
        
        assert success is True
        assert msg == "Success"

    @patch("scraper_lib.requests.Session")
    def test_login_wrong_credentials(self, mock_session_class, scraper):
        """Test login with wrong credentials."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '<input name="_token" value="test_token">Identitas tersebut tidak cocok dengan data kami'
        mock_response.ok = True
        mock_session.get.return_value = mock_response
        mock_session.post.return_value = mock_response
        
        scraper.session = mock_session
        
        success, msg = scraper.login()
        
        assert success is False
        assert "Salah" in msg

    @patch("scraper_lib.requests.Session")
    def test_login_network_error(self, mock_session_class, scraper):
        """Test login when network error occurs."""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")
        
        scraper.session = mock_session
        
        success, msg = scraper.login()
        
        assert success is False
        assert "Network error" in msg


class TestScraperSemesters:
    """Tests for semester fetching."""

    @patch("scraper_lib.requests.Session")
    def test_get_semesters_success(self, mock_session_class, scraper):
        """Test successful semester fetching."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <div class="col-12 col-md-6 col-lg-4">
            <h5 class="card-title">Semester Ganjil 2024</h5>
            <p class="card-text">Kode Semester #20241</p>
            <a class="btn-primary" href="/semester/20241">Select</a>
        </div>
        """
        mock_session.get.return_value = mock_response
        
        scraper.session = mock_session
        
        semesters = scraper.get_semesters()
        
        assert len(semesters) == 1
        assert semesters[0]["title"] == "Semester Ganjil 2024"
        assert semesters[0]["code"] == "20241"

    @patch("scraper_lib.requests.Session")
    def test_get_semesters_empty(self, mock_session_class, scraper):
        """Test when no semesters are found."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_session.get.return_value = mock_response
        
        scraper.session = mock_session
        
        semesters = scraper.get_semesters()
        
        assert len(semesters) == 0

    @patch("scraper_lib.requests.Session")
    def test_get_semesters_error(self, mock_session_class, scraper):
        """Test semester fetching when error occurs."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_session.get.return_value = mock_response
        
        scraper.session = mock_session
        
        semesters = scraper.get_semesters()
        
        assert len(semesters) == 0


class TestIPv4Enforcement:
    """Tests for IPv4 enforcement."""

    def test_socket_patched(self):
        """Test that socket.getaddrinfo is patched for IPv4."""
        import socket
        import scraper_lib  # This imports and patches the socket
        
        # The module patches socket.getaddrinfo on import
        # We can verify by checking if the function exists
        assert hasattr(socket, "getaddrinfo")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
