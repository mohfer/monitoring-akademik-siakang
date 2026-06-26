"""Script Worker untuk Monitoring Akademik Siakang.

Script ini berjalan sebagai subprocess dan memantau halaman Siakang Untirta secara berkala.

Mode Monitoring:
- Monitoring Nilai: Mengecek perubahan nilai atau nilai baru di halaman Hasil Studi
- Monitoring KRS: Mengecek ketersediaan Mata Kuliah tertentu di halaman KRS (Livewire)

Notifikasi:
- Telegram: Menggunakan Bot API dengan Markdown formatting
- WhatsApp: Menggunakan WAHA (WhatsApp HTTP API)

Konfigurasi melalui Environment Variables yang diinjeksi oleh server/manager.py.
Script ini didesain untuk dijalankan standalone atau via subprocess.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
import sys
from dotenv import load_dotenv
import builtins
from datetime import datetime
import re
import html
import atexit
from scraper_lib import BrowserSession
from colorama import Fore, Style, init

init(autoreset=True)

def print(*args, **kwargs):
    now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    msg = ' '.join(str(arg) for arg in args)
    
    if '[ERROR]' in msg or '[GAGAL]' in msg:
        colored_msg = msg.replace('[ERROR]', f'{Fore.RED}[ERROR]{Style.RESET_ALL}').replace('[GAGAL]', f'{Fore.RED}[GAGAL]{Style.RESET_ALL}')
    elif '[SUCCESS]' in msg or '[SUKSES]' in msg:
        colored_msg = msg.replace('[SUCCESS]', f'{Fore.GREEN}[SUCCESS]{Style.RESET_ALL}').replace('[SUKSES]', f'{Fore.GREEN}[SUKSES]{Style.RESET_ALL}')
    elif '[WARNING]' in msg or '[PERINGATAN]' in msg:
        colored_msg = msg.replace('[WARNING]', f'{Fore.YELLOW}[WARNING]{Style.RESET_ALL}').replace('[PERINGATAN]', f'{Fore.YELLOW}[PERINGATAN]{Style.RESET_ALL}')
    elif '[INFO]' in msg:
        colored_msg = msg.replace('[INFO]', f'{Fore.CYAN}[INFO]{Style.RESET_ALL}')
    elif '[STATUS]' in msg:
        colored_msg = msg.replace('[STATUS]', f'{Fore.BLUE}[STATUS]{Style.RESET_ALL}')
    elif '[ALERT]' in msg:
        colored_msg = msg.replace('[ALERT]', f'{Fore.MAGENTA}[ALERT]{Style.RESET_ALL}')
    elif '[COMPLETE]' in msg:
        colored_msg = msg.replace('[COMPLETE]', f'{Fore.GREEN + Style.BRIGHT}[COMPLETE]{Style.RESET_ALL}')
    elif '[UPDATE]' in msg:
        colored_msg = msg.replace('[UPDATE]', f'{Fore.CYAN}[UPDATE]{Style.RESET_ALL}')
    else:
        colored_msg = msg
    
    builtins.print(f"{Fore.WHITE}{now}{Style.RESET_ALL}", colored_msg, **kwargs)

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

URL_LOGIN = "https://siakang.untirta.ac.id/auth/login"
URL_TARGET = "https://siakang.untirta.ac.id/hasil-studi"
URL_LIST_SEMESTER = "https://siakang.untirta.ac.id/dashboard/list-semester"

LOGIN_ID = os.getenv("LOGIN_ID")
PASSWORD = os.getenv("PASSWORD")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

WAHA_BASE_URL = os.getenv("WAHA_BASE_URL")
WAHA_SESSION = os.getenv("WAHA_SESSION", "default")
WAHA_API_KEY = os.getenv("WAHA_API_KEY")

WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER")

FILE_DATA = os.getenv("FILE_DATA")
INTERVAL = int(os.getenv("INTERVAL", 300))
TARGET_SEMESTER_CODE = os.getenv("TARGET_SEMESTER_CODE")

MONITOR_TYPE = os.getenv("MONITOR_TYPE", "nilai")
TARGET_COURSES_STR = os.getenv("TARGET_COURSES")
try:
    TARGET_COURSES = json.loads(TARGET_COURSES_STR) if TARGET_COURSES_STR else []
except:
    TARGET_COURSES = []

URL_KRS = "https://siakang.untirta.ac.id/krs-mahasiswa"

SELECTED_SEMESTER_URL = None

session = BrowserSession()
atexit.register(session.close)

def send_telegram(message):
    """
    Mengirim pesan teks ke bot Telegram yang dikonfigurasi.
    """
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return
            if response.status_code >= 400 and response.status_code < 500:
                print(f"[WARNING] Telegram API Error: {response.text}")
                return
        except Exception as e:
            print(f"[WARNING] Gagal kirim Telegram (Percobaan {attempt+1}/3): {e}")
        
        if attempt < 2:
            time.sleep(5)

def send_waha(message):
    """
    Mengirim pesan teks via WAHA (WhatsApp HTTP API).
    """
    if not WAHA_BASE_URL:
        return
        
    target_number = WHATSAPP_NUMBER
    if not target_number and CHAT_ID and CHAT_ID.isdigit():
        target_number = CHAT_ID
        
    if not target_number:
        return

    wa_message = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', message)
    
    target_number = str(target_number).strip()
    
    if '@' not in target_number:
        sanitized = re.sub(r'[^0-9]', '', target_number)
        if sanitized:
            target_number = f"{sanitized}@c.us"
    
    url = f"{WAHA_BASE_URL}/api/sendText"
    payload = {
        "chatId": target_number,
        "text": wa_message,
        "session": WAHA_SESSION
    }
    
    headers = {}
    if WAHA_API_KEY:
        headers["X-Api-Key"] = WAHA_API_KEY
    
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 201 or response.status_code == 200:
                return
            print(f"[WARNING] WAHA API Error: {response.text}")
        except Exception as e:
            print(f"[WARNING] Gagal kirim WAHA (Percobaan {attempt+1}/3): {e}")
        
        if attempt < 2:
            time.sleep(2)

def send_notification(message):
    """Wrapper untuk mengirim ke semua channel yang tersedia."""
    if TELEGRAM_TOKEN and CHAT_ID:
        send_telegram(message)
    
    if WAHA_BASE_URL and WHATSAPP_NUMBER:
        send_waha(message)

def do_login():
    """Melakukan proses login untuk mendapatkan session cookie."""
    try:
        print("[INFO] Mencoba login ke Siakang...")
        success, msg = session.login(LOGIN_ID, PASSWORD)
        if not success:
            if msg == "Identitas Salah":
                print("[ERROR] Login gagal: Identitas (NIM/Password) salah.")
            else:
                print(f"[ERROR] Login gagal: {msg}")
            return False

        print("[SUCCESS] Login berhasil.")
        if SELECTED_SEMESTER_URL:
            print("[INFO] Mengaktifkan kembali semester terpilih...")
            try:
                session.get(SELECTED_SEMESTER_URL)
                print("[SUCCESS] Semester berhasil diaktifkan ulang.")
            except Exception as e:
                print(f"[WARNING] Gagal mengaktifkan ulang semester: {e}")
        return True
    except Exception as e:
        print(f"[ERROR] Error saat login: {e}")
    return False

def get_all_semesters():
    """Mengambil semua daftar semester yang tersedia dengan pagination."""
    print("[INFO] Mengambil daftar semester...")
    semesters = []
    current_url = URL_LIST_SEMESTER
    
    while current_url:
        try:
            res = session.get(current_url)
            if res.status_code != 200:
                print(f"[WARNING] Gagal akses list semester: {res.status_code}")
                break

            soup = BeautifulSoup(res.text, 'html.parser')
            
            cards = soup.find_all('div', class_='col-12 col-md-6 col-lg-4')
            for card in cards:
                title_elm = card.find('h5', class_='card-title')
                if not title_elm: continue
                
                title = title_elm.get_text(strip=True)
                
                code_elm = card.find('p', class_='card-text')
                code = code_elm.get_text(strip=True).replace("Kode Semester #", "") if code_elm else ""
                
                link_elm = card.find('a', class_='btn-primary')
                url = link_elm['href'] if link_elm else None
                
                if title and url:
                    semesters.append({
                        'title': title,
                        'code': code,
                        'url': url
                    })

            next_link = soup.find('a', rel='next')
            if next_link and next_link.has_attr('href'):
                current_url = next_link['href']
                if not current_url.startswith('http'):
                    pass
            else:
                current_url = None
                
        except Exception as e:
            print(f"[WARNING] Error parsing list semester: {e}")
            break
            
    return semesters

def get_data():
    """Mengambil data nilai menggunakan session yang ada."""
    try:
        res = session.get(URL_TARGET)
        
        if res.status_code != 200:
            print(f"[WARNING] Server Kampus memberikan respon tidak normal: {res.status_code}")
            return []

        soup_target = BeautifulSoup(res.text, 'html.parser')

        try:
            hitung_ips_link = None
            for a_tag in soup_target.find_all('a'):
                if "Hitung IPS" in a_tag.get_text():
                    hitung_ips_link = a_tag['href']
                    break
            
            if hitung_ips_link:
                print("[INFO] Menjalankan proses Hitung IPS...")
                session.get(hitung_ips_link)
                res = session.get(URL_TARGET)
                soup_target = BeautifulSoup(res.text, 'html.parser')
        except Exception as e:
            print(f"[WARNING] Gagal menjalankan Hitung IPS: {e}")

        tbody = soup_target.find('tbody')

        if not tbody:
            if "auth/login" in res.url:
                print("[WARNING] Sesi habis (Redirect ke login).")
            else:
                print("[WARNING] Tabel tidak ditemukan (Sesi gantung/halaman error).")
            
            print("[INFO] Memaksa login ulang untuk menyegarkan sesi...")
            if do_login():
                res = session.get(URL_TARGET)
                soup_target = BeautifulSoup(res.text, 'html.parser')
                tbody = soup_target.find('tbody')
            
            if not tbody:
                print("[ERROR] Masih gagal mendapatkan tabel setelah login ulang. Server mungkin sedang down.")
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
                        except:
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
                    "mutu": "---" if (is_placeholder or is_empty) else col_mutu.get_text(strip=True)
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
            print(f"[WARNING] Gagal parsing IP/IPK: {e}")
        
        user_name = "-"
        user_nim = LOGIN_ID
        
        try:
            name_elem = soup_target.select_one('.pro-user-name')
            if name_elem:
                full_text = name_elem.get_text(strip=True)
                user_name = full_text
            else:
                user_box_name = soup_target.select_one('.user-box .dropdown-toggle')
                if user_box_name:
                    user_name = user_box_name.get_text(strip=True)
                    
            user_name = user_name.replace("", "").strip()
                
        except Exception as e:
            print(f"[WARNING] Gagal parsing Nama User: {e}")

        final_data = {
            "nama": user_name,
            "nim": user_nim,
            "ips": ip_val,
            "ipk": ipk_val,
            "total_sks": total_sks,
            "nilai": results
        }

        return final_data

    except Exception as e:
        print(f"[ERROR] Error serius di get_data: {e}")
        return None

def get_krs_data():
    """Mengambil data ketersediaan matkul di halaman KRS."""
    try:
        print(f"[INFO] Mengakses halaman KRS: {URL_KRS}")
        res = session.get(URL_KRS)
        
        if res.status_code != 200:
            print(f"[WARNING] Gagal akses KRS: {res.status_code}")
            return None

        if "auth/login" in res.url:
            print("[WARNING] Sesi habis (Redirect ke login).")
            if do_login():
                res = session.get(URL_KRS)
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
            print("[WARNING] Gagal mendapatkan CSRF Token untuk request Livewire.")
            return None

        target_component_name = "rencana-studi.rencana-studi-index"
        snapshot = None
        component_id = None

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
            print(f"[WARNING] Komponen Livewire '{target_component_name}' tidak ditemukan.")
            return None

        print(f"[SUCCESS] Livewire Component Found: ID={component_id}")

        if '"lazyIsolated":true' in snapshot or '"lazyLoaded":false' in snapshot:
            print("[INFO] Component is Lazy Loaded. Waking it up...")
            
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
                'User-Agent': session.headers['User-Agent']
            }
            
            hydrate_payload = {
                "_token": csrf_token,
                "components": [
                    {
                        "snapshot": snapshot,
                        "updates": {},
                        "calls": [
                            {
                                "path": "",
                                "method": "__lazyLoad",
                                "params": lazy_params
                            }
                        ]
                    }
                ]
            }
            
            try:
                h_res = session.post(hydrate_url, json=hydrate_payload, headers=headers)
                if h_res.status_code == 200:
                    h_json = h_res.json()
                    new_snapshot = h_json['components'][0].get('snapshot')
                    if new_snapshot:
                        snapshot = new_snapshot
                        print("[SUCCESS] Component hydrated! Snapshot updated.")
                    else:
                        print("[WARNING] Hydration succeeded but no new snapshot returned.")
                else:
                    print(f"[WARNING] Failed to hydrate lazy component ({h_res.status_code})")
            except Exception as e:
                print(f"[WARNING] Error during hydration: {e}")

        found_courses = []
        
        livewire_url = f"{res.url.split('/krs-mahasiswa')[0]}/livewire/update"
        
        headers = {
            'X-Livewire': 'true',
            'X-CSRF-TOKEN': csrf_token,
            'Content-Type': 'application/json',
            'Origin': 'https://siakang.untirta.ac.id',
            'Referer': URL_KRS, 
            'User-Agent': session.headers['User-Agent']
        }

        for course_name in TARGET_COURSES:
            if not course_name: continue
            
            print(f"[INFO] Mencari matkul: {course_name}...")
            
            payload = {
                "_token": csrf_token,
                "components": [
                    {
                        "snapshot": snapshot,
                        "updates": {
                            "search": course_name
                        },
                        "calls": []
                    }
                ]
            }
            
            try:
                p_res = session.post(livewire_url, json=payload, headers=headers)
                
                if p_res.status_code != 200:
                    print(f"[WARNING] Gagal search ({p_res.status_code})")
                    if p_res.status_code == 419:
                        print("[WARNING] Token expired, re-login next loop.")
                        break
                    continue

                try:
                    resp_json = p_res.json()
                    c_effects = resp_json.get('components', [{}])[0].get('effects', {})
                    html_content = c_effects.get('html', '')
                    decoded_html = html.unescape(html_content)

                    if course_name.lower() in decoded_html.lower():
                        print(f"[SUCCESS] DITEMUKAN!")
                        found_courses.append(course_name)
                    
                except json.JSONDecodeError:
                        print("[WARNING] Response bukan valid JSON")
            
            except Exception as e:
                print(f"[WARNING] Error during search request: {e}")
            
            time.sleep(1)

        return {"found": found_courses}

    except Exception as e:
        print(f"[ERROR] Error get_krs_data: {e}")
        return None

def monitor():
    """
    Loop utama monitoring.
    1. Login ke sistem.
    2. Cek tipe monitoring (Nilai / KRS).
    3. Jalankan loop sesuai tipe.
    """
    global SELECTED_SEMESTER_URL
    
    run_once = "--run-once" in sys.argv
    MONITOR_TEXT = "KRS" if MONITOR_TYPE == 'krs' else "NILAI"
    print(f"[INFO] Monitoring Akademik Siakang ({MONITOR_TEXT}) Dimulai... {'(Mode Sekali Jalan)' if run_once else ''}")
    
    if not do_login():
        print("[ERROR] Login awal gagal. Hentikan script.")
        return

    SELECTED_SEMESTER_TITLE = ""
    semesters = get_all_semesters()
    
    if semesters:
        selected = None
        if TARGET_SEMESTER_CODE:
            print(f"[INFO] Mencari semester dengan kode konfigurasi: {TARGET_SEMESTER_CODE}")
            for sem in semesters:
                if sem['code'] == TARGET_SEMESTER_CODE:
                    selected = sem
                    break
            if not selected:
                print(f"[ERROR] Semester dengan kode '{TARGET_SEMESTER_CODE}' tidak ditemukan. Menggunakan default.")
        
        
        if selected:
            SELECTED_SEMESTER_URL = selected['url']
            SELECTED_SEMESTER_TITLE = selected['title']
            print(f"[SUCCESS] Memilih Semester: {selected['title']}")
            print("[INFO] Mengaktifkan semester...")
            session.get(SELECTED_SEMESTER_URL)
            time.sleep(1)
        else:
            print("[INFO] Menggunakan semester aktif saat ini (tidak ada perubahan).")

    if MONITOR_TYPE == 'krs':
        print(f"[INFO] Target Matkul ({len(TARGET_COURSES)}): {', '.join(TARGET_COURSES)}")
        if not TARGET_COURSES:
            print("[WARNING] Tidak ada matkul yang ditargetkan! Pastikan konfigurasi 'Target Courses' diisi.")

        while True:
            try:
                data = get_krs_data() 
                next_check = time.strftime('%H:%M:%S', time.localtime(time.time() + INTERVAL))
                
                if data:
                    current_found = set(data['found'])
                    
                    old_found = set()
                    if os.path.exists(FILE_DATA):
                        try:
                            with open(FILE_DATA, "r") as f:
                                old_data = json.load(f)
                                if isinstance(old_data, dict):
                                    old_found = set(old_data.get('found', []))
                        except Exception:
                            pass
                    
                    newly_found = current_found - old_found
                    
                    if newly_found:
                        msg = "🔔 *MATKUL DITEMUKAN DI KRS!*\n"
                        for course in newly_found:
                            msg += f"✅ {course}\n"
                        
                        if len(current_found) >= len(TARGET_COURSES) and len(TARGET_COURSES) > 0:
                             msg += "\n🎉 *SEMUA MATKUL INCARAN LENGKAP!* 💯\nSegera 'Ambil' sekarang sebelum habis!\n"

                        msg += f"\nCek segera di: [KRS Online]({URL_KRS})"
                        send_notification(msg)
                        print(f"[SUCCESS] Ditemukan {len(newly_found)} matkul baru yang sebelumnya tidak ada.")
                    
                    lost_found = old_found - current_found
                    if lost_found:
                        print(f"[INFO] Matkul hilang dari pencarian: {', '.join(lost_found)}")

                    print(f"[STATUS] Status: {len(current_found)}/{len(TARGET_COURSES)} matkul ditemukan. (Next: {next_check})")
                    
                    with open(FILE_DATA, "w") as f:
                        json.dump({"found": list(current_found)}, f)
                else:
                    print(f"[WARNING] Gagal mendapatkan data KRS. (Next: {next_check})")
                
            except Exception as e:
                print(f"[ERROR] Error loop KRS: {e}")
                import traceback
                traceback.print_exc()
            
            if run_once: break
            time.sleep(INTERVAL)
        return

    if not semesters:
        print("[WARNING] Tidak dapat menemukan daftar semester. Menggunakan default sistem.")

    while True:
        old_data = None
        try:
            current_data = get_data()
            next_check = time.strftime('%H:%M:%S', time.localtime(time.time() + INTERVAL))
            
            if not current_data:
                print(f"[WARNING] Data kosong atau gagal diambil. Akan dicoba lagi pada: {next_check}")
            elif os.path.exists(FILE_DATA):
                try:
                    with open(FILE_DATA, "r") as f:
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
                for cur, old in zip(current_courses, old_courses):
                    if old['nilai'] != cur['nilai']:
                        semester_info = f"🎓 *{SELECTED_SEMESTER_TITLE}*\n\n" if SELECTED_SEMESTER_TITLE else ""
                        msg = (f"🔔 *NILAI KELUAR!*\n"
                                f"{semester_info}"
                                f"📚 *Matkul:* {cur['matkul']}\n"
                                f"📊 *Nilai:* `{cur['nilai']}`\n"
                                f"✨ *Mutu:* `{cur['mutu']}`\n\n"
                                f"Cek di: [Siakang Untirta]({URL_TARGET})")
                        changes.append(msg)
                
                if isinstance(old_data, dict):
                    if old_data.get('ips') != current_data.get('ips') and current_data.get('ips') != "-":
                         changes.append(f"📈 *IPS Berubah*: {old_data.get('ips')} -> {current_data.get('ips')}")
                    if old_data.get('ipk') != current_data.get('ipk') and current_data.get('ipk') != "-":
                         changes.append(f"📈 *IPK Berubah*: {old_data.get('ipk')} -> {current_data.get('ipk')}")

                if changes:
                    for change in changes:
                        send_notification(change)
                    print(f"[SUCCESS] Terdeteksi {len(changes)} perubahan nilai! (Cek lagi: {next_check})")
                else:
                    print(f"[STATUS] Tidak ada perubahan. (Terakhir: {time.strftime('%H:%M:%S')} | Berikutnya: {next_check})")
            
            if current_data:
                current_courses = current_data.get('nilai', [])
                is_complete = all(d['nilai'] != "---" for d in current_courses)
                
                was_complete = False
                if old_data:
                    old_c = old_data if isinstance(old_data, list) else old_data.get('nilai', [])
                    was_complete = all(d['nilai'] != "---" for d in old_c)
            
                if is_complete and not was_complete and len(current_courses) > 0:
                    semester_info = f"🎓 *{SELECTED_SEMESTER_TITLE}*\n\n" if SELECTED_SEMESTER_TITLE else ""
                    msg_complete = (f"🎉 *SEMUA NILAI SUDAH KELUAR!*\n"
                                    f"{semester_info}"
                                    f"👤 *{current_data.get('nama')}*\n"
                                    f"📈 *IPS:* {current_data.get('ips')} | *IPK:* {current_data.get('ipk')}\n"
                                    f"Silakan cek portal Siakang untuk detail lengkap.\n"
                                    f"[Login Siakang]({URL_TARGET})")
                    send_notification(msg_complete)
                    print("[SUCCESS] Notifikasi semua nilai keluar telah dikirim!")

            if current_data:
                with open(FILE_DATA, "w") as f:
                    json.dump(current_data, f, indent=4)
                
        except Exception as e:
            print(f"[ERROR] Error di loop monitor: {e}")
            import traceback
            traceback.print_exc()
        
        if run_once:
            print("[SUCCESS] Selesai (Mode Sekali Jalan).")
            break
            
        time.sleep(INTERVAL)

if __name__ == "__main__":
    monitor()