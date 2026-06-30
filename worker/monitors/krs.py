"""KRS monitor: checks target course availability on the Livewire KRS page."""

import html
import json
import os
import re
import time
import traceback

from bs4 import BeautifulSoup

from ..config import URL_KRS
from ..logging_setup import log
from .base import BaseMonitor


class KrsMonitor(BaseMonitor):
    """Monitors the KRS page for availability of target courses."""

    label = "KRS"

    def fetch(self):
        """Fetch course availability data on the KRS page."""
        try:
            log(f"[INFO] Accessing KRS page: {URL_KRS}")
            res = self.session.get(URL_KRS)

            if res.status_code != 200:
                log(f"[WARNING] Failed to access KRS: {res.status_code}")
                return None

            if "auth/login" in res.url:
                log("[WARNING] Session expired (Redirect to login).")
                if self.login():
                    res = self.session.get(URL_KRS)
                else:
                    return None

            soup = BeautifulSoup(res.text, 'html.parser')
            csrf_token = None

            script_csrf = soup.find('script', {'data-csrf': True})
            if script_csrf:
                csrf_token = script_csrf['data-csrf']

            if not csrf_token:
                meta_csrf = soup.find('meta', {'name': 'csrf-token'})
                if meta_csrf:
                    csrf_token = meta_csrf['content']

            if not csrf_token:
                input_csrf = soup.find('input', {'name': '_token'})
                if input_csrf:
                    csrf_token = input_csrf['value']

            if not csrf_token:
                log("[WARNING] Failed to get CSRF Token for Livewire request.")
                return None

            target_component_name = "rencana-studi.rencana-studi-index"
            snapshot = None
            component_id = None
            full_tag = None

            tag_match = re.search(r'<[^>]+wire:snapshot="[^"]*rencana-studi\.rencana-studi-index[^"]*"[^>]*>', res.text)

            if tag_match:
                full_tag = tag_match.group(0)
                id_match = re.search(r'wire:id=["\']([^"\']+)["\']', full_tag)
                if id_match:
                    component_id = id_match.group(1)

                snap_match = re.search(r'wire:snapshot=(["\'])(.*?)\1', full_tag)
                if snap_match:
                    raw_snapshot = snap_match.group(2)
                    snapshot = html.unescape(raw_snapshot)

            if not snapshot or not component_id:
                log(f"[WARNING] Livewire component '{target_component_name}' not found.")
                return None

            log(f"[SUCCESS] Livewire Component Found: ID={component_id}")

            if '"lazyIsolated":true' in snapshot or '"lazyLoaded":false' in snapshot:
                log("[INFO] Component is Lazy Loaded. Waking it up...")

                lazy_params = []
                x_intersect_match = re.search(r'x-intersect=["\']([^"\']+)["\']', full_tag)
                if x_intersect_match:
                    x_val_raw = x_intersect_match.group(1)
                    x_val = html.unescape(x_val_raw)
                    lazy_arg_match = re.search(r"\$wire\.__lazyLoad\(['\"]([^'\"]+)['\"]\)", x_val)
                    if lazy_arg_match:
                        lazy_params = [lazy_arg_match.group(1)]

                hydrate_url = f"{res.url.split('/krs-mahasiswa')[0]}/livewire/update"

                headers = {
                    'X-Livewire': 'true',
                    'X-CSRF-TOKEN': csrf_token,
                    'Content-Type': 'application/json',
                    'User-Agent': self.session.headers['User-Agent'],
                }

                hydrate_payload = {
                    "_token": csrf_token,
                    "components": [
                        {
                            "snapshot": snapshot,
                            "updates": {},
                            "calls": [
                                {"path": "", "method": "__lazyLoad", "params": lazy_params}
                            ],
                        }
                    ],
                }

                try:
                    h_res = self.session.post(hydrate_url, json=hydrate_payload, headers=headers)
                    if h_res.status_code == 200:
                        h_json = h_res.json()
                        new_snapshot = h_json['components'][0].get('snapshot')
                        if new_snapshot:
                            snapshot = new_snapshot
                            log("[SUCCESS] Component hydrated! Snapshot updated.")
                        else:
                            log("[WARNING] Hydration succeeded but no new snapshot returned.")
                    else:
                        log(f"[WARNING] Failed to hydrate lazy component ({h_res.status_code})")
                except Exception as e:
                    log(f"[WARNING] Error during hydration: {e}")

            found_courses = []

            livewire_url = f"{res.url.split('/krs-mahasiswa')[0]}/livewire/update"

            headers = {
                'X-Livewire': 'true',
                'X-CSRF-TOKEN': csrf_token,
                'Content-Type': 'application/json',
                'Origin': 'https://siakang.untirta.ac.id',
                'Referer': URL_KRS,
                'User-Agent': self.session.headers['User-Agent'],
            }

            for course_name in self.config.target_courses:
                if not course_name:
                    continue

                log(f"[INFO] Searching for course: {course_name}...")

                payload = {
                    "_token": csrf_token,
                    "components": [
                        {"snapshot": snapshot, "updates": {"search": course_name}, "calls": []}
                    ],
                }

                try:
                    p_res = self.session.post(livewire_url, json=payload, headers=headers)

                    if p_res.status_code != 200:
                        log(f"[WARNING] Search failed ({p_res.status_code})")
                        if p_res.status_code == 419:
                            log("[WARNING] Token expired, re-login next loop.")
                            break
                        continue

                    try:
                        resp_json = p_res.json()
                        c_effects = resp_json.get('components', [{}])[0].get('effects', {})
                        html_content = c_effects.get('html', '')
                        decoded_html = html.unescape(html_content)

                        if course_name.lower() in decoded_html.lower():
                            log("[SUCCESS] DITEMUKAN!")
                            found_courses.append(course_name)

                    except json.JSONDecodeError:
                        log("[WARNING] Response is not valid JSON")

                except Exception as e:
                    log(f"[WARNING] Error during search request: {e}")

                time.sleep(1)

            return {"found": found_courses}

        except Exception as e:
            log(f"[ERROR] Error in get_krs_data: {e}")
            return None

    def loop(self, run_once):
        c = self.config

        log(f"[INFO] Target Courses ({len(c.target_courses)}): {', '.join(c.target_courses)}")
        if not c.target_courses:
            log("[WARNING] No target courses specified! Make sure 'Target Courses' configuration is filled.")

        while True:
            try:
                data = self.fetch()
                next_check = time.strftime('%H:%M:%S', time.localtime(time.time() + c.interval))

                if data:
                    current_found = set(data['found'])

                    old_found = set()
                    if os.path.exists(c.file_data):
                        try:
                            with open(c.file_data, "r") as f:
                                old_data = json.load(f)
                                if isinstance(old_data, dict):
                                    old_found = set(old_data.get('found', []))
                        except Exception:
                            pass

                    newly_found = current_found - old_found

                    if newly_found:
                        msg = "\U0001F514 *MATKUL DITEMUKAN DI KRS!*\n"
                        for course in newly_found:
                            msg += f"✅ {course}\n"

                        if len(current_found) >= len(c.target_courses) and len(c.target_courses) > 0:
                            msg += "\n\U0001F389 *SEMUA MATKUL INCARAN LENGKAP!* \U0001F4AF\nSegera 'Ambil' sekarang sebelum habis!\n"

                        msg += f"\nCek segera di: [KRS Online]({URL_KRS})"
                        self.notifier.send(msg)
                        log(f"[SUCCESS] Found {len(newly_found)} new courses not previously available.")

                    lost_found = old_found - current_found
                    if lost_found:
                        log(f"[INFO] Courses removed from search: {', '.join(lost_found)}")

                    log(f"[STATUS] Status: {len(current_found)}/{len(c.target_courses)} courses found. (Next: {next_check})")

                    with open(c.file_data, "w") as f:
                        json.dump({"found": list(current_found)}, f)
                else:
                    log(f"[WARNING] Failed to get KRS data. (Next: {next_check})")

            except Exception as e:
                log(f"[ERROR] Error in KRS loop: {e}")
                traceback.print_exc()

            if run_once:
                break
            time.sleep(c.interval)
