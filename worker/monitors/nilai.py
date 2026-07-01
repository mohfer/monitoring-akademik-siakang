"""Grade monitor: detects new/changed grades on the Study Results page."""

import json
import os
import time
import traceback

from bs4 import BeautifulSoup

from ..config import URL_TARGET
from ..logging_setup import log
from .base import BaseMonitor


class GradeMonitor(BaseMonitor):
    """Monitors the 'hasil-studi' page for grade and GPA changes."""

    label = "NILAI"

    def fetch(self):
        """Fetch grade data using the existing session."""
        try:
            res = self.session.get(URL_TARGET)

            if res.status_code != 200:
                log(f"[WARNING] Campus server returned abnormal response: {res.status_code}")
                return []

            soup_target = BeautifulSoup(res.text, 'html.parser')

            try:
                hitung_ips_link = None
                for a_tag in soup_target.find_all('a'):
                    if "Hitung IPS" in a_tag.get_text():
                        hitung_ips_link = a_tag['href']
                        break

                if hitung_ips_link:
                    log("[INFO] Running IPS calculation process...")
                    self.session.get(hitung_ips_link)
                    res = self.session.get(URL_TARGET)
                    soup_target = BeautifulSoup(res.text, 'html.parser')
            except Exception as e:
                log(f"[WARNING] Failed to run IPS calculation: {e}")

            tbody = soup_target.find('tbody')

            if not tbody:
                if "auth/login" in res.url:
                    log("[WARNING] Session expired (Redirect to login).")
                else:
                    log("[WARNING] Table not found (Session hung/error page).")

                log("[INFO] Forcing re-login to refresh session...")
                if self.login():
                    res = self.session.get(URL_TARGET)
                    soup_target = BeautifulSoup(res.text, 'html.parser')
                    tbody = soup_target.find('tbody')

                if not tbody:
                    log("[ERROR] Still failed to get table after re-login. Server may be down.")
                    return []

            results = []
            rows = tbody.find_all('tr')
            total_sks = 0

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6 and not row.get('class'):
                    matkul_cell = cols[2]

                    sks_val = 0
                    for badge in matkul_cell.find_all('span', class_='badge'):
                        badge_text = badge.get_text(strip=True)
                        if "SKS" in badge_text:
                            try:
                                sks_val = int(badge_text.replace("SKS", "").strip())
                            except ValueError:
                                pass
                        badge.decompose()

                    total_sks += sks_val
                    matkul = matkul_cell.get_text(strip=True)

                    col_nilai = cols[4]
                    col_mutu = cols[5]

                    is_placeholder = "placeholder" in str(col_nilai)
                    is_empty = not col_nilai.get_text(strip=True)

                    results.append({
                        "matkul": matkul,
                        "sks": sks_val,
                        "nilai": "---" if (is_placeholder or is_empty) else col_nilai.get_text(strip=True),
                        "mutu": "---" if (is_placeholder or is_empty) else col_mutu.get_text(strip=True),
                    })

            ip_val = "-"
            ipk_val = "-"
            try:
                for p in soup_target.find_all('p'):
                    text = p.get_text(strip=True)
                    if "IP :" in text and "IPK" not in text:
                        ip_val = text.split(":")[-1].strip()
                    elif "IPK :" in text:
                        ipk_val = text.split(":")[-1].strip()
            except Exception as e:
                log(f"[WARNING] Failed to parse GPA/CGPA: {e}")

            user_name = "-"
            user_nim = self.config.login_id

            try:
                name_elem = soup_target.select_one('.pro-user-name')
                if name_elem:
                    user_name = name_elem.get_text(strip=True)
                else:
                    user_box_name = soup_target.select_one('.user-box .dropdown-toggle')
                    if user_box_name:
                        user_name = user_box_name.get_text(strip=True)

                user_name = user_name.replace("", "").strip()

            except Exception as e:
                log(f"[WARNING] Failed to parse user name: {e}")

            return {
                "nama": user_name,
                "nim": user_nim,
                "ips": ip_val,
                "ipk": ipk_val,
                "total_sks": total_sks,
                "nilai": results,
            }

        except Exception as e:
            log(f"[ERROR] Critical error in get_data: {e}")
            return None

    def _grade_message(self, cur, with_grades=True):
        """Build a grade notification. If with_grades=False, omit scores."""
        semester_info = f"🎓 *{self.selected_semester_title}*\n\n" if self.selected_semester_title else ""
        if not with_grades:
            return (f"🔔 *NILAI KELUAR!*\n"
                    f"{semester_info}"
                    f"\U0001F4DA *Matkul:* {cur['matkul']}\n\n"
                    f"Cek di: [Siakang Untirta]({URL_TARGET})")
        return (f"🔔 *NILAI KELUAR!*\n"
                f"{semester_info}"
                f"\U0001F4DA *Matkul:* {cur['matkul']}\n"
                f"\U0001F4CA *Nilai:* `{cur['nilai']}`\n"
                f"✨ *Mutu:* `{cur['mutu']}`\n\n"
                f"Cek di: [Siakang Untirta]({URL_TARGET})")

    def loop(self, run_once):
        c = self.config

        if not self.semesters:
            log("[WARNING] Cannot find semester list. Using system default.")

        while True:
            old_data = None
            try:
                current_data = self.fetch()
                next_check = time.strftime('%H:%M:%S', time.localtime(time.time() + c.interval))

                if not current_data:
                    log(f"[WARNING] Data is empty or failed to fetch. Will retry at: {next_check}")
                else:
                    # Run change detection whenever we have data. If no baseline
                    # file exists yet (first run / after reset), old_data stays
                    # None -> old_courses empty -> the branch below notifies every
                    # grade that is already out (empty -> grades appearing).
                    if os.path.exists(c.file_data):
                        try:
                            with open(c.file_data, "r") as f:
                                old_data = json.load(f)
                        except Exception:
                            old_data = None

                    old_courses = []
                    if isinstance(old_data, list):
                        old_courses = old_data
                    elif isinstance(old_data, dict):
                        old_courses = old_data.get('nilai', [])

                    current_courses = current_data.get('nilai', [])

                    changes = []

                    if old_courses:
                        for cur, old in zip(current_courses, old_courses):
                            if old['nilai'] != cur['nilai']:
                                changes.append(cur)

                        if isinstance(old_data, dict):
                            if old_data.get('ips') != current_data.get('ips') and current_data.get('ips') != "-":
                                changes.append(f"\U0001F4C8 *IPS Berubah*: {old_data.get('ips')} -> {current_data.get('ips')}")
                            if old_data.get('ipk') != current_data.get('ipk') and current_data.get('ipk') != "-":
                                changes.append(f"\U0001F4C8 *IPK Berubah*: {old_data.get('ipk')} -> {current_data.get('ipk')}")
                    else:
                        for cur in current_courses:
                            if cur['nilai'] and cur['nilai'] != "---":
                                changes.append(cur)

                    if old_courses and len(current_courses) > len(old_courses):
                        for cur in current_courses[len(old_courses):]:
                            if cur['nilai'] and cur['nilai'] != "---":
                                changes.append(cur)

                    if changes:
                        for change in changes:
                            if isinstance(change, dict):
                                tg_msg = self._grade_message(change, not self.config.notify_without_grades_telegram)
                                wa_msg = self._grade_message(change, not self.config.notify_without_grades_whatsapp)
                                self.notifier.send_per_channel(tg_msg, wa_msg)
                            else:
                                tg_msg = change if not self.config.notify_without_grades_telegram else None
                                wa_msg = change if not self.config.notify_without_grades_whatsapp else None
                                self.notifier.send_per_channel(tg_msg, wa_msg)
                        log(f"[SUCCESS] Detected {len(changes)} grade changes! (Check again: {next_check})")
                    else:
                        log(f"[STATUS] No changes. (Last: {time.strftime('%H:%M:%S')} | Next: {next_check})")

                if current_data:
                    current_courses = current_data.get('nilai', [])
                    is_complete = all(d['nilai'] != "---" for d in current_courses)

                    was_complete = False
                    if old_data:
                        old_c = old_data if isinstance(old_data, list) else old_data.get('nilai', [])
                        was_complete = all(d['nilai'] != "---" for d in old_c)

                    if is_complete and not was_complete and len(current_courses) > 0:
                        semester_info = f"\U0001F393 *{self.selected_semester_title}*\n\n" if self.selected_semester_title else ""
                        msg_complete = (f"\U0001F389 *SEMUA NILAI SUDAH KELUAR!*\n"
                                        f"{semester_info}"
                                        f"\U0001F464 *{current_data.get('nama')}*\n"
                                        f"\U0001F4C8 *IPS:* {current_data.get('ips')} | *IPK:* {current_data.get('ipk')}\n"
                                        f"Silakan cek portal Siakang untuk detail lengkap.\n"
                                        f"[Login Siakang]({URL_TARGET})")
                        tg_msg = msg_complete if not self.config.notify_without_grades_telegram else None
                        wa_msg = msg_complete if not self.config.notify_without_grades_whatsapp else None
                        self.notifier.send_per_channel(tg_msg, wa_msg)
                        log("[SUCCESS] All grades released notification sent!")

                if current_data:
                    with open(c.file_data, "w") as f:
                        json.dump(current_data, f, indent=4)

            except Exception as e:
                log(f"[ERROR] Error in monitor loop: {e}")
                traceback.print_exc()

            if run_once:
                log("[SUCCESS] Completed (Run Once Mode).")
                break

            time.sleep(c.interval)
