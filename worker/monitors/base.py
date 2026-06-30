"""Shared monitor primitives: login, semester listing/selection, run loop."""

import sys
import time

from bs4 import BeautifulSoup

from scraper_lib import BrowserSession

from ..config import URL_LIST_SEMESTER
from ..logging_setup import log


class BaseMonitor:
    """Base class holding the browser session and shared portal helpers.

    Subclasses implement :meth:`loop` (and typically a ``fetch`` method) for a
    specific monitoring mode (grades or KRS).
    """

    label = "MONITOR"

    def __init__(self, config, notifier, session=None):
        self.config = config
        self.notifier = notifier
        self.session = session or BrowserSession()
        self.selected_semester_url = None
        self.selected_semester_title = ""
        self.semesters = []

    def login(self):
        """Log in to Siakang, reactivating the selected semester if any."""
        c = self.config
        try:
            log("[INFO] Trying to login to Siakang...")
            success, msg = self.session.login(c.login_id, c.password)
            if not success:
                if msg == "Identitas Salah":
                    log("[ERROR] Login failed: Invalid credentials (NIM/Password).")
                else:
                    log(f"[ERROR] Login failed: {msg}")
                return False

            log("[SUCCESS] Login successful.")
            if self.selected_semester_url:
                log("[INFO] Reactivating selected semester...")
                try:
                    self.session.get(self.selected_semester_url)
                    log("[SUCCESS] Semester reactivated successfully.")
                except Exception as e:
                    log(f"[WARNING] Failed to reactivate semester: {e}")
            return True
        except Exception as e:
            log(f"[ERROR] Error during login: {e}")
        return False

    def get_all_semesters(self):
        """Fetch all available semesters, following pagination."""
        log("[INFO] Fetching semester list...")
        semesters = []
        current_url = URL_LIST_SEMESTER

        while current_url:
            try:
                res = self.session.get(current_url)
                if res.status_code != 200:
                    log(f"[WARNING] Failed to access semester list: {res.status_code}")
                    break

                soup = BeautifulSoup(res.text, 'html.parser')

                cards = soup.find_all('div', class_='col-12 col-md-6 col-lg-4')
                for card in cards:
                    title_elm = card.find('h5', class_='card-title')
                    if not title_elm:
                        continue

                    title = title_elm.get_text(strip=True)

                    code_elm = card.find('p', class_='card-text')
                    code = code_elm.get_text(strip=True).replace("Kode Semester #", "") if code_elm else ""

                    link_elm = card.find('a', class_='btn-primary')
                    url = link_elm['href'] if link_elm else None

                    if title and url:
                        semesters.append({'title': title, 'code': code, 'url': url})

                next_link = soup.find('a', rel='next')
                if next_link and next_link.has_attr('href'):
                    current_url = next_link['href']
                    if not current_url.startswith('http'):
                        pass
                else:
                    current_url = None

            except Exception as e:
                log(f"[WARNING] Error parsing semester list: {e}")
                break

        return semesters

    def select_semester(self):
        """Pick and activate the configured semester (if specified)."""
        c = self.config
        semesters = self.get_all_semesters()

        if semesters:
            selected = None
            if c.target_semester_code:
                log(f"[INFO] Searching for semester with config code: {c.target_semester_code}")
                for sem in semesters:
                    if sem['code'] == c.target_semester_code:
                        selected = sem
                        break
                if not selected:
                    log(f"[ERROR] Semester with code '{c.target_semester_code}' not found. Using default.")

            if selected:
                self.selected_semester_url = selected['url']
                self.selected_semester_title = selected['title']
                log(f"[SUCCESS] Selected Semester: {selected['title']}")
                log("[INFO] Activating semester...")
                self.session.get(self.selected_semester_url)
                time.sleep(1)
            else:
                log("[INFO] Using current active semester (no changes).")

        return semesters

    def run(self):
        """Login, select the semester, then enter the mode-specific loop."""
        run_once = "--run-once" in sys.argv
        log(f"[INFO] Siakang Academic Monitoring ({self.label}) Started... "
            f"{'(Run Once Mode)' if run_once else ''}")

        if not self.login():
            log("[ERROR] Initial login failed. Stopping script.")
            return

        self.semesters = self.select_semester()
        self.loop(run_once)

    def loop(self, run_once):  # pragma: no cover - implemented by subclasses
        raise NotImplementedError
