"""Scraper Library for Siakang Untirta (Playwright-based).

Since Siakang was equipped with Cloudflare anti-bot challenge, request-based
`requests`/`curl_cffi` can no longer login (POST login hits JS challenge).
This library replaces it with a real Chromium browser (Playwright) that
executes the Cloudflare JavaScript challenge.

Components:
- BrowserSession: Chromium wrapper that mimics requests.Session interface
  (`.get()`, `.post()`, `.headers`) to minimize changes in main.py.
- SiakangScraper: used by API endpoint `/check-semesters` for login validation
  and fetching semester list.

Headless note: Cloudflare here rejects chrome-headless-shell (old Playwright
headless mode), but allows `channel="chromium"` (new headless).
So BrowserSession always uses chromium channel to run on servers
without display.
"""

import json
import socket
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Force IPv4 for socket-based connections (e.g. requests for notifications).
# Does not affect Chromium, only maintains requests connectivity as before.
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

BASE_URL = "https://siakang.untirta.ac.id"
URL_LOGIN = f"{BASE_URL}/auth/login"
URL_LIST_SEMESTER = f"{BASE_URL}/dashboard/list-semester"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Cloudflare interstitial page titles to wait for until they disappear.
CF_TITLES = {"Just a moment...", "Tunggu sebentar..."}


class Resp:
    """Minimal response object mimicking requests.Response."""

    def __init__(self, text, url, status_code):
        self.text = text
        self.url = url
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)

    @property
    def ok(self):
        return 200 <= self.status_code < 400


class BrowserSession:
    """Chromium wrapper (Playwright) with requests.Session-like interface."""

    def __init__(self):
        self.headers = {"User-Agent": USER_AGENT}
        self._pw = None
        self._browser = None
        self._ctx = None
        self.page = None

    def start(self):
        if self.page is not None:
            return
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            channel="chromium",  # new headless mode; passes Cloudflare
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self._ctx = self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="id-ID",
        )
        self._ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        self.page = self._ctx.new_page()

    def _wait_cf(self, timeout=90):
        """Wait until Cloudflare interstitial disappears. Returns final title."""
        deadline = time.time() + timeout
        title = ""
        while time.time() < deadline:
            try:
                title = self.page.title()
            except Exception:
                title = ""
            if title and title not in CF_TITLES:
                return title
            time.sleep(2)
        return title

    def get(self, url):
        self.start()
        response = self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self._wait_cf()
        status = response.status if response is not None else 200
        return Resp(self.page.content(), self.page.url, status)

    def post(self, url, json=None, headers=None, **kwargs):
        """POST via fetch inside page (same-origin), automatically passes Cloudflare.

        Used for Livewire requests (KRS). Carries cookie context as-is.
        """
        self.start()
        result = self.page.evaluate(
            """async ({url, payload, headers}) => {
                const r = await fetch(url, {
                    method: 'POST',
                    headers: headers || {},
                    body: JSON.stringify(payload),
                    credentials: 'include',
                });
                const text = await r.text();
                return {status: r.status, text};
            }""",
            {"url": url, "payload": json, "headers": headers or {}},
        )
        return Resp(result["text"], url, result["status"])

    def login(self, login_id, password):
        """Login to Siakang. Returns (success: bool, message: str)."""
        try:
            self.start()
            self.get(URL_LOGIN)
            if not self.page.query_selector("input[name='email']"):
                return False, "Login form not found (possibly blocked by Cloudflare)"

            self.page.fill("input[name='email']", login_id)
            self.page.fill("input[name='password']", password)
            self.page.click("button[type='submit']")
            self.page.wait_for_load_state("domcontentloaded")
            self._wait_cf()

            content = self.page.content()
            if "Identitas tersebut tidak cocok dengan data kami" in content:
                return False, "Identitas Salah"
            if "/auth/login" in self.page.url:
                return False, "Login failed (still on login page)"
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def close(self):
        for obj, method in (
            (self._ctx, "close"),
            (self._browser, "close"),
            (self._pw, "stop"),
        ):
            try:
                if obj is not None:
                    getattr(obj, method)()
            except Exception:
                pass
        self._ctx = self._browser = self._pw = self.page = None


class SiakangScraper:
    """Login validation + fetch semester list. Used by API endpoint."""

    def __init__(self, login_id, password):
        self.login_id = login_id
        self.password = password
        self.session = BrowserSession()

    def login(self):
        success, msg = self.session.login(self.login_id, self.password)
        if not success:
            self.session.close()
        return success, msg

    def get_semesters(self):
        """Fetch all semesters with pagination support.

        Returns:
            list: List of dicts with keys 'title', 'code', and 'url'.
        """
        semesters = []
        current_url = URL_LIST_SEMESTER
        try:
            while current_url:
                res = self.session.get(current_url)
                if res.status_code != 200:
                    break

                soup = BeautifulSoup(res.text, "html.parser")
                cards = soup.find_all("div", class_="col-12 col-md-6 col-lg-4")
                for card in cards:
                    title_elm = card.find("h5", class_="card-title")
                    if not title_elm:
                        continue
                    title = title_elm.get_text(strip=True)

                    code_elm = card.find("p", class_="card-text")
                    code = (
                        code_elm.get_text(strip=True).replace("Kode Semester #", "")
                        if code_elm
                        else ""
                    )

                    link_elm = card.find("a", class_="btn-primary")
                    url = link_elm["href"] if link_elm else None

                    if title and code:
                        semesters.append({"title": title, "code": code, "url": url})

                next_link = soup.find("a", rel="next")
                current_url = (
                    next_link["href"]
                    if next_link and next_link.has_attr("href")
                    else None
                )
        finally:
            self.session.close()
        return semesters
