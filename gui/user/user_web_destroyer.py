import os
import json
import time
import random
import hashlib
import threading
import requests
import webbrowser
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import customtkinter as ctk
from tkinter import messagebox, Tk
import asyncio
import aiohttp 

# ==============================
# Paths & config
# ==============================
ROOT = os.getcwd()
RESULTS_DIR = os.path.join(ROOT, "results")
SCREEN_DIR = os.path.join(RESULTS_DIR, "screenshots")
DATA_DIR = os.path.join(ROOT, "data")
STORE_PATH = os.path.join(DATA_DIR, "generated_texts.json")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(SCREEN_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

REPORT_PAGE_GOOGLE = "https://safebrowsing.google.com/safebrowsing/report_phish/"
REPORT_PAGE_ADUAN = "https://aduankonten.id/"

UA = UserAgent()

# ==============================
# Slot keywords + captcha/block keywords
# ==============================
SLOT_KEYWORDS = [
    "slot", "slots", "gacor", "jackpot", "spin", "maxwin", "rtp", "scatter",
    "bonus", "bet", "permainan", "putaran", "jackpot", "pragmatic", "habanero",
    "live casino", "mesin slot", "deposit", "withdraw", "jackpot", "jackpot besar"
]

CAPTCHA_KEYWORDS = ["captcha", "recaptcha", "are you human", "please verify", "please complete the security check"]

BLOCK_HOST_KEYWORDS = ["internetbaik", "trustpositif", "nawala", "blocked", "internetpositif"]

# ==============================
# Helper: User-Agent Generator
# ==============================
def get_random_user_agent():
    try:
        return UA.random
    except:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"

# ==============================
# Helper: clipboard
# ==============================
def copy_to_clipboard(text: str):
    r = Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(text)
    r.update()
    r.destroy()

# ==============================
# Helper: unique text generator (persist store)
# ==============================
TEMPLATES = [
    "{domain} terindikasi menyediakan konten permainan slot/gambling yang berpotensi merugikan pengguna.",
    "Terindikasi aktivitas perjudian/slot di domain {domain}; mohon verifikasi dan tindakan lebih lanjut.",
    "Halaman di {domain} menampilkan elemen terkait slot/judi (mis. deposit, jackpot, spin).",
    "{domain} menunjukkan pola situs perjudian (slot) yang dapat merugikan pengguna."
]
NOTES = [
    "Analisis otomatis; verifikasi manual disarankan.",
    "Simpan bukti (screenshot/html) sebelum submit.",
    "Jika benar berbau judi/slot, lanjut manual submit ke pihak berwenang."
]

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _load_store():
    if not os.path.exists(STORE_PATH):
        return {"hashes": []}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"hashes": []}

def _save_store(store: dict):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

def _mark_seen(h: str):
    s = _load_store()
    if "hashes" not in s:
        s["hashes"] = []
    if h not in s["hashes"]:
        s["hashes"].append(h)
        _save_store(s)

def generate_unique_text(domain: str, reason: str = None) -> str:
    tries = 0
    while tries < 8:
        tries += 1
        t = random.choice(TEMPLATES).format(domain=domain)
        if reason:
            t = f"{t} Alasan: {reason}."
        h = _sha256_hex(t)
        if h not in _load_store().get("hashes", []):
            _mark_seen(h)
            return t
    token = hashlib.sha1(os.urandom(8)).hexdigest()[:6]
    final = f"{random.choice(TEMPLATES).format(domain=domain)} [{token}]"
    _mark_seen(_sha256_hex(final))
    return final

def generate_note():
    return random.choice(NOTES)

# ==============================
# Fetch snippet (tetap gunakan requests/sync agar Playwright aman)
# ==============================
def fetch_snippet(url: str, timeout: int = 10) -> dict:
    try:
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
        html = resp.text or ""
        final = resp.url
        status = resp.status_code
        history = [h.url for h in resp.history] if resp.history else []
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        meta = None
        m = soup.find("meta", attrs={"name": "description"})
        if m and m.get("content"):
            meta = m.get("content").strip()
        text_lower = soup.get_text(" ", strip=True).lower() if html else ""
        found = sorted(list({kw for kw in SLOT_KEYWORDS if kw in text_lower}))
        captcha_found = any(k in text_lower for k in CAPTCHA_KEYWORDS)
        js_redirects = []
        for s in soup.find_all("script"):
            if s.string and ("window.location" in s.string or "location.href" in s.string):
                import re
                js_redirects += re.findall(r'["\'](https?://[^"\']+)["\']', s.string)
        redirects = history[:]
        if final and final not in redirects:
            redirects.append(final)
        return {
            "status": status,
            "final_url": final,
            "redirects": redirects,
            "title": title,
            "meta": meta,
            "slot_keywords_found": found,
            "captcha_detected": captcha_found,
            "js_redirects": js_redirects,
            "html_snapshot": html[:2000]
        }
    except Exception as e:
        return {"error": str(e)}

# ==============================
# Screenshot helper (Playwright sync)
# ==============================
def capture_screenshot(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright tidak terpasang. Install: pip install playwright ; python -m playwright install") from exc

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(ch for ch in urlparse(url).netloc if ch.isalnum() or ch in ("-","_"))[:40] or "site"
    fname = f"{ts}_{safe}.png"
    path = os.path.join(SCREEN_DIR, fname)
    p = sync_playwright().start()
    try:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=get_random_user_agent())
        page.goto(url, timeout=20000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.screenshot(path=path, full_page=True)
        browser.close()
    finally:
        try:
            p.stop()
        except Exception:
            pass
    return path

# ==============================
# Detect block / recaptcha heuristics
# ==============================
def detect_block(snippet: dict) -> dict:
    blocked = False
    reasons = []
    status = snippet.get("status")
    if status in (403, 429):
        blocked = True
        reasons.append(f"status_{status}")
    final = (snippet.get("final_url") or "").lower()
    if any(b in final for b in BLOCK_HOST_KEYWORDS):
        blocked = True
        reasons.append("redirect_block_host")
    if snippet.get("captcha_detected"):
        blocked = True
        reasons.append("captcha_keyword")
    return {"blocked": blocked, "reasons": reasons}

# ==============================
# Save report
# ==============================
def save_report_file(report: dict) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(ch for ch in report.get("domain","site") if ch.isalnum() or ch in ("-_"))[:40]
    fname = f"{ts}_{safe}_slotreport.json"
    path = os.path.join(RESULTS_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path

# ==============================
# GUI Class
# ==============================
class SlotReporterUI(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        # Inisialisasi loop asyncio
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.post_thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self.post_thread.start()

        ctk.CTkLabel(self, text="🎰 Slot Site Reporter (Filter + Evidence)", font=("Roboto", 20, "bold")).pack(pady=(8,6))
        ctk.CTkLabel(self, text="Tool ini hanya menyiapkan laporan untuk situs yang TERDETEKSI berbau slot. Manual submit ke layanan publik.", text_color="#AAAAAA", wraplength=860).pack(pady=(0,8))

        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=12, pady=(6,8))
        ctk.CTkLabel(frm, text="Target URL:", anchor="w").pack(fill="x")
        self.url_entry = ctk.CTkEntry(frm, placeholder_text="https://example-slot-site.com/page", width=760)
        self.url_entry.pack(fill="x", pady=(6,8))

        ctk.CTkLabel(frm, text="Optional note/reason:", anchor="w").pack(fill="x")
        self.reason_entry = ctk.CTkEntry(frm, placeholder_text="(opsional)", width=560)
        self.reason_entry.pack(fill="x", pady=(6,8))

        btnfrm = ctk.CTkFrame(self)
        btnfrm.pack(fill="x", padx=12, pady=(4,8))
        ctk.CTkButton(btnfrm, text="🔎 Scan & Analyze", command=self._start_scan).pack(side="left", padx=6)
        ctk.CTkButton(btnfrm, text="📷 Capture Screenshot (optional)", command=self._take_screenshot).pack(side="left", padx=6)
        ctk.CTkButton(btnfrm, text="💾 Save Report (if slot)", command=self._save_report).pack(side="left", padx=6)
        
        ctk.CTkButton(btnfrm, text="🚀 Simulasi POST (Aiohttp Async)", 
                      command=self._start_auto_post_simulasi, 
                      fg_color="#CC00CC", hover_color="#990099").pack(side="left", padx=12)

        ctk.CTkButton(btnfrm, text="🌐 Open Google Report Page", command=lambda: self._open_url(REPORT_PAGE_GOOGLE)).pack(side="right", padx=6)
        ctk.CTkButton(btnfrm, text="🌐 Open AduanKonten", command=lambda: self._open_url(REPORT_PAGE_ADUAN)).pack(side="right", padx=6)

        self.progress = ctk.CTkProgressBar(self, width=760, variable=ctk.DoubleVar(value=0.0))
        self.progress.pack(padx=12, pady=(6,8))

        self.log_box = ctk.CTkTextbox(self, height=360, font=("Consolas", 11))
        self.log_box.pack(fill="both", padx=12, pady=(0,12))

        self.analysis = None
        self.screenshot_path = None

    def _run_async_loop(self):
        self.loop.run_forever()

    # ------------------------------
    # UI helpers
    # ------------------------------
    def _log(self, text: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{datetime.utcnow().isoformat()} - {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _open_url(self, u: str):
        webbrowser.open(u)

    # ------------------------------
    # Scan & analyze (thread)
    # ------------------------------
    def _start_scan(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input", "Masukkan target URL dulu bro.")
            return
        if not url.lower().startswith("http"):
            url = "https://" + url
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, url)

        th = threading.Thread(target=self._scan_task, args=(url,), daemon=True)
        th.start()

    def _scan_task(self, url: str):
        try:
            self.progress.set(0.05)
            self._log(f"Start scanning {url}")
            time.sleep(random.uniform(0.4, 1.0))

            snippet = fetch_snippet(url)
            self.progress.set(0.45)
            if snippet.get("error"):
                self._log(f"Fetch error: {snippet.get('error')}")
                self.analysis = {"error": snippet.get("error")}
                return

            domain = urlparse(url).netloc
            found = snippet.get("slot_keywords_found", [])
            self._log(f"Title: {snippet.get('title')}")
            self._log(f"Meta: {snippet.get('meta') or '-'}")
            self._log(f"HTTP Status: {snippet.get('status')}")
            if snippet.get("redirects"):
                self._log(f"Redirects: {', '.join(snippet.get('redirects')[:5])}")

            is_slot = bool(found)
            if is_slot:
                self._log(f"✅ Slot keywords FOUND: {', '.join(found)}")
            else:
                self._log("⚠️ No slot-related keywords found — will NOT create report automatically.")
            
            det = detect_block(snippet)
            if det.get("blocked"):
                self._log(f"⚠️ Block/Captcha heuristics: {', '.join(det.get('reasons',[]))}")

            generated_text = generate_unique_text(domain, reason=self.reason_entry.get().strip() or None) if is_slot else None
            note = generate_note() if is_slot else None

            report = {
                "scanned_at": datetime.utcnow().isoformat() + "Z",
                "domain": domain,
                "target_url": url,
                "is_slot_candidate": is_slot,
                "slot_keywords_found": found,
                "snippet": snippet,
                "detected_block": det,
                "generated_text": generated_text,
                "note": note,
                "screenshot": None
            }
            self.analysis = report
            self.screenshot_path = None
            self.progress.set(1.0)
            self._log("Scan complete.")
        except Exception as e:
            self._log(f"Scan exception: {e}")

    # ------------------------------
    # Screenshot (thread)
    # ------------------------------
    def _take_screenshot(self):
        if not self.analysis:
            messagebox.showwarning("No data", "Lakukan Scan dulu sebelum screenshot.")
            return
        url = self.analysis.get("target_url")
        th = threading.Thread(target=self._screenshot_task, args=(url,), daemon=True)
        th.start()

    def _screenshot_task(self, url: str):
        try:
            self._log("📷 Capturing screenshot (Playwright required)...")
            p = capture_screenshot(url)
            self.screenshot_path = p
            if self.analysis:
                self.analysis["screenshot"] = p
            self._log(f"Screenshot saved: {p}")
        except Exception as e:
            self._log(f"Screenshot failed: {e}")
            self._log("Install Playwright: pip install playwright ; then: python -m playwright install")

    # ------------------------------
    # Save report (only if slot)
    # ------------------------------
    def _save_report(self):
        if not self.analysis:
            messagebox.showwarning("No data", "Lakukan Scan dulu sebelum Save.")
            return
        if not self.analysis.get("is_slot_candidate"):
            messagebox.showwarning("Not allowed", "Halaman ini tidak mengandung indikasi slot — tidak dibuat laporan.")
            self._log("Save aborted: not a slot candidate.")
            return
        
        if self.screenshot_path and not self.analysis.get("screenshot"):
            self.analysis["screenshot"] = self.screenshot_path
        
        if not self.analysis.get("generated_text"):
            domain = self.analysis.get("domain")
            self.analysis["generated_text"] = generate_unique_text(domain, reason=self.reason_entry.get().strip() or None)
            self.analysis["note"] = generate_note()
            
        path = save_report_file(self.analysis)
        self._log(f"Saved report file: {path}")
        
        details = f"{self.analysis.get('generated_text')}\n\n{self.analysis.get('note')}\n\nEvidence:\nTitle: {self.analysis['snippet'].get('title')}\nMeta: {self.analysis['snippet'].get('meta')}\nFound keywords: {', '.join(self.analysis.get('slot_keywords_found', []))}"
        copy_to_clipboard(details)
        self._log("Details copied to clipboard (ready to paste into report form).")
        messagebox.showinfo("Saved", f"Report saved to:\n{path}\n\nDetails copied to clipboard for manual paste.")

    # ------------------------------
    # POST Report (Async) - SIMULASI (AIOHTTP)
    # ------------------------------
    def _start_auto_post_simulasi(self):
        if not self.analysis or not self.analysis.get("is_slot_candidate"):
            messagebox.showwarning("No Data", "Lakukan Scan dulu, dan pastikan terdeteksi kandidat slot sebelum Auto POST.")
            return
        
        # Jalankan fungsi async di event loop yang terpisah
        asyncio.run_coroutine_threadsafe(self._submit_report_task(self.analysis), self.loop)

    async def _submit_report_task(self, report: dict):
        self.progress.set(0.0)
        self._log(f"⚡ Attempting POST to simulated endpoint (Async): {REPORT_PAGE_GOOGLE}")
        
        target_url = report.get("target_url")
        details_text = report.get("generated_text")

        if not details_text:
            domain = report.get("domain")
            details_text = generate_unique_text(domain, reason=self.reason_entry.get().strip() or None)
            
        payload_json = {
            'reportType': 'Halaman ini tidak aman', 
            'url': target_url,
            'details': details_text,
        }

        headers = {
            "User-Agent": get_random_user_agent(),
            "Content-Type": "application/json" 
        }

        try:
            self._log(f"Sending JSON payload (aiohttp) for URL: {target_url}...")
            
            # Menggunakan aiohttp.ClientSession
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(REPORT_PAGE_GOOGLE, json=payload_json, timeout=15) as response:
                    
                    status_code = response.status
                    response_text = await response.text()
                    
                    if status_code == 200:
                        self._log(f"✅ Auto POST Berhasil! Status Code: {status_code}")
                        self._log("Respon server (200 OK): " + response_text[:100] + "...")
                        messagebox.showinfo("Auto POST Success", f"POST berhasil terkirim ke {REPORT_PAGE_GOOGLE}. Cek server lokal Anda.")
                    elif status_code == 405:
                        self._log(f"❌ Auto POST Gagal! Status Code: 405 (Method Not Allowed). Coba cek metode POST di server Anda.")
                        messagebox.showerror("POST Failed (405)", "Status 405: Server tidak mengizinkan metode POST ke URL ini.")
                    else:
                        self._log(f"❌ Auto POST Gagal! Status Code: {status_code}")
                        self.log_box.insert("end", "Respon Gagal: " + response_text[:100] + "...\n")
                        messagebox.showerror("Auto POST Failed", f"POST gagal dengan Status Code: {status_code}. Cek log dan endpoint.")
        
        except asyncio.TimeoutError:
            self._log("❌ Error Koneksi saat POST: Timeout reached.")
            messagebox.showerror("Connection Error", "Gagal terhubung: Request timeout.")
        except Exception as e:
            self._log(f"❌ Error Koneksi saat POST: {e}")
            messagebox.showerror("Connection Error", f"Gagal terhubung atau error tak terduga: {e}")
        finally:
            self.progress.set(1.0)

# ==============================
# Run standalone
# ==============================
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    root.title("Slot Reporter — Safe")
    root.geometry("980x760")
    SlotReporterUI(root).pack(fill="both", expand=True)
    root.mainloop()