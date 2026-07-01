"""Centralized worker configuration.

All values are read from environment variables. When the worker runs as a
subprocess these are injected by ``server/manager.py``; for standalone runs
they come from ``.env`` (loaded here once).
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

# Target endpoints on the Siakang portal.
URL_TARGET = "https://siakang.untirta.ac.id/hasil-studi"
URL_LIST_SEMESTER = "https://siakang.untirta.ac.id/dashboard/list-semester"
URL_KRS = "https://siakang.untirta.ac.id/krs-mahasiswa"


def _parse_courses(raw):
    """Parse the TARGET_COURSES JSON string, tolerating malformed input."""
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


class WorkerConfig:
    """Snapshot of worker settings read from the environment."""

    def __init__(self):
        self.login_id = os.getenv("LOGIN_ID")
        self.password = os.getenv("PASSWORD")

        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("CHAT_ID")

        self.waha_base_url = os.getenv("WAHA_BASE_URL")
        self.waha_session = os.getenv("WAHA_SESSION", "default")
        self.waha_api_key = os.getenv("WAHA_API_KEY")
        self.whatsapp_number = os.getenv("WHATSAPP_NUMBER")

        self.file_data = os.getenv("FILE_DATA")
        self.interval = int(os.getenv("INTERVAL", 300))
        self.target_semester_code = os.getenv("TARGET_SEMESTER_CODE")

        self.monitor_type = os.getenv("MONITOR_TYPE", "nilai")
        self.target_courses = _parse_courses(os.getenv("TARGET_COURSES"))
        self.notify_without_grades_telegram = os.getenv("NOTIFY_WITHOUT_GRADES_TELEGRAM", "0") == "1"
        self.notify_without_grades_whatsapp = os.getenv("NOTIFY_WITHOUT_GRADES_WHATSAPP", "0") == "1"


config = WorkerConfig()
