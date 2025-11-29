import asyncio
import random
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Library eksternal yang dibutuhkan
from fake_useragent import UserAgent
from playwright.async_api import Browser, Error as PlaywrightError, async_playwright
from PIL import Image, ImageTk

# ==============================
# KONFIGURASI UMUM & PLAYWRIGHT
# ==============================
CONCURRENT_DEFAULT = 1
PLAYWRIGHT_TIMEOUT = 90_000 # Increased timeout (90 seconds)
MAX_RETRIES_PER_VISIT = 3 

# Playwright-specific settings (DWELL, SCROLL, FORMS)
SCROLL_MIN = 200
SCROLL_MAX = 800
SCROLL_STEPS_MIN = 3
SCROLL_STEPS_MAX = 7
DWELL_MIN_MS = 5_000 # Increased dwell time
DWELL_MAX_MS = 10_000 # Increased dwell time

# Screenshot Preview Size (Max dimension for the preview panel)
MAX_PREVIEW_WIDTH = 450
MAX_PREVIEW_HEIGHT = 450 

MOCK_DATA = {
    "name": "Budi Santoso",
    "email": "budi.santoso" + str(random.randint(100, 999)) + "@mail.com",
    "phone": "0812" + str(random.randint(1000000, 9000000)),
    "message": "Ini pesan simulasi dari traffic injector dari Playwright.",
    "username": "user" + str(random.randint(1000, 9999)),
    "password": "Password123",
}

# Googlebot UA string
# Menggunakan Googlebot Mobile Smartphone UA
GOOGLEBOT_UA = "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.86 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


# ==============================
# Playwright Helper Functions
# ==============================

def _rand_viewport(ua_mode: str = "Random Browser"):
    if ua_mode == "Googlebot":
        return {"width": 400, "height": 700} 
    else:
        # Browser Random menggunakan ukuran acak
        return {"width": random.randint(1024, 1920), "height": random.randint(600, 1080)}

async def _dismiss_overlays(page):
    """Menutup overlay/popup."""
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(500)
    selectors = ["div.modal.show", "div[role='dialog'].show", "div[id*='popup']", "div[class*='popup']", "div[class*='overlay']"]
    for sel in selectors:
        for modal in await page.query_selector_all(sel):
            btn = await modal.query_selector("button.close, button[data-dismiss], .btn-close, [aria-label='Close']")
            if btn:
                try:
                    await btn.click()
                    await page.wait_for_timeout(500)
                except Exception:
                    pass

async def _human_scroll(page):
    """Simulasi scrolling yang lambat dan acak."""
    for _ in range(random.randint(SCROLL_STEPS_MIN, SCROLL_STEPS_MAX)):
        await page.mouse.wheel(0, random.randint(SCROLL_MIN, SCROLL_MAX))
        await page.wait_for_timeout(random.randint(1_500, 3_500)) # Ditingkatkan

async def _interactive_back_and_forth(page, domain, log):
    """Mencari, mengklik link internal, menunggu, lalu kembali ke halaman sebelumnya."""
    anchors = await page.query_selector_all("a[href]")
    internal = [a for a in anchors if domain in ((await a.get_attribute("href")) or "")]
    
    if not internal:
        log("   ℹ️ No internal links found for interaction.")
        return
    
    visible_internal = [a for a in internal if await a.is_visible() and await a.is_enabled() and (await a.get_attribute('href')).startswith(('http', '/'))]
            
    if not visible_internal:
        log(" No visible internal links found for interaction.")
        return
        
    try:
        chosen_link = random.choice(visible_internal)
        href = await chosen_link.get_attribute("href")
        
        log(f"   ➡️ Clicking internal link: {href[:50]}...")
        
        await chosen_link.click(timeout=15_000) # Timeout ditingkatkan
        await page.wait_for_load_state("networkidle")
        
        await page.wait_for_timeout(random.randint(5_000, 10_000)) # Dwell time ditingkatkan
        await _human_scroll(page)
        
        await page.go_back(timeout=20_000, wait_until="domcontentloaded")
        await page.wait_for_timeout(random.randint(3_000, 5_000))
        
    except Exception as e:
        log(f"   ⚠️ Interaction failed ({e.__class__.__name__}) — skipping back/forward.")
    else:
        log("   ✔ Interaksi (Click + Back) berhasil.")

async def _auto_interact_with_forms(page, log):
    """Mencari form dan mengisi field yang relevan."""
    forms = await page.query_selector_all("form")
    
    if not forms:
        log("   ℹ️ No forms found on page.")
        return

    log(f"   ✨ Found {len(forms)} form(s). Attempting interaction...")

    for i, form in enumerate(forms):
        try:
            inputs = await form.query_selector_all('input[type="text"], input[type="email"], input[type="tel"], input[type="password"], textarea')
            filled_count = 0
            
            for input_field in inputs:
                if not await input_field.is_visible() or not await input_field.is_enabled(): continue
                        
                input_name = await input_field.get_attribute('name')
                input_id = await input_field.get_attribute('id')
                input_type = await input_field.get_attribute('type')
                tag_name = await page.evaluate('(element) => element.tagName', input_field) 
                    
                input_label = (input_name or input_id or "").lower()
                value = None
                
                if input_type == 'email' or ('email' in input_label):
                    value = MOCK_DATA["email"]
                elif input_type == 'password':
                    value = MOCK_DATA["password"]
                elif 'user' in input_label or 'username' in input_label:
                    value = MOCK_DATA["username"]
                elif 'nama' in input_label or 'name' in input_label or 'fullname' in input_label:
                    value = MOCK_DATA["name"]
                elif input_type == 'tel' or ('phone' in input_label or 'telp' in input_label):
                    value = MOCK_DATA["phone"]
                elif tag_name == 'TEXTAREA' or ('message' in input_label or 'comment' in input_label):
                    value = MOCK_DATA["message"]

                if value:
                    try:
                        await input_field.fill(value, timeout=500)
                        filled_count += 1
                    except Exception:
                        pass

            if filled_count > 0:
                log(f"     ✏️ Form {i+1}: Filled {filled_count} field(s).")

            submit_btn = await form.query_selector('button[type="submit"], input[type="submit"]')
            
            if submit_btn and await submit_btn.is_visible():
                await submit_btn.click(timeout=7000)
                log(f"     ✔ Form {i+1} submitted.")
                await page.wait_for_timeout(3000)
            else:
                log(f"     ℹ️ Form {i+1}: No submit button visible.")
                
        except Exception as e:
            log(f"     ❌ Form {i+1} interaction failed: {e.__class__.__name__}")

async def _get_public_ip_via_playwright(browser: Browser, proxy_server: str, proxy_user: str, proxy_pass: str) -> str:
    """Mendapatkan IP public melalui proxy (Playwright)."""
    ip_checker_url = "https://api.ipify.org" 
    
    context = await browser.new_context(
        proxy={"server": proxy_server, "username": proxy_user, "password": proxy_pass},
        ignore_https_errors=True,
    )
    page = await context.new_page()
    ip_address = "IP_NOT_FOUND"

    try:
        await page.goto(ip_checker_url, wait_until="domcontentloaded", timeout=15000)
        ip_address = await page.evaluate("document.body.textContent.trim()")
        if not ip_address or not ip_address.replace('.', '').isdigit():
             ip_address = "IP_INVALID_RESPONSE"
    except PlaywrightError:
        ip_address = "IP_CHECK_FAILED"
    except Exception:
        ip_address = "IP_CHECK_ERROR"
    finally:
        await context.close()
    
    return ip_address

async def _playwright_visit(browser: Browser, target: str, ua: str, proxy_server: str, proxy_user: str, proxy_pass: str, ip_public: str, log, semaphore: asyncio.Semaphore, show_ss_callback, ua_mode: str):
    """Logika kunjungan menggunakan Playwright (Browser Mode)."""
    async with semaphore:
        log(f"[Browser] IP {ip_public} visiting target {target}.")
        
        for attempt in range(1, MAX_RETRIES_PER_VISIT + 1):
            log(f"  ↳ attempt {attempt}/{MAX_RETRIES_PER_VISIT} (UA: {ua[:30]}...)")

            # FIX: Hapus keyword argument 'timeout' dari new_context()
            context = await browser.new_context(
                user_agent=ua,
                viewport=_rand_viewport(ua_mode), 
                proxy={"server": proxy_server, "username": proxy_user, "password": proxy_pass},
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                # 1. AKSES AWAL
                # Meningkatkan timeout untuk rendering yang lebih lama
                await page.goto(target, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT)
                
                if page.url == "about:blank":
                    raise PlaywrightError("Page failed to load (Blank URL).")
                
                # Tambahan waktu tunggu untuk memastikan semua script Googlebot version termuat
                await page.wait_for_timeout(random.randint(4000, 8000))
                
                # SCREENSHOT AKSES AWAL (LIVE PREVIEW)
                ss_initial_path = Path(f"temp_ss_{random.randint(1000, 9999)}_initial.png")
                await page.screenshot(path=ss_initial_path)
                show_ss_callback(ss_initial_path) 
                log("   📸 Initial page loaded. Live preview updated.")
                
                # 2. INTERAKSI
                domain = urlparse(target).netloc
                await _dismiss_overlays(page)
                await page.wait_for_timeout(random.randint(DWELL_MIN_MS, DWELL_MAX_MS))
                await _human_scroll(page)
                
                await _auto_interact_with_forms(page, log) 
                await _interactive_back_and_forth(page, domain, log) 
                
                # 3. FALLBACK KE URL TARGET
                current_url_base = urlparse(page.url)._replace(query=None).geturl()
                target_url_base = urlparse(target)._replace(query=None).geturl()
                
                if current_url_base != target_url_base:
                    log(f"   🔙 Navigating back to target URL: {target}")
                    await page.goto(target, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(random.randint(3000, 5000))
                
                # 4. SCREENSHOT AKHIR (FINAL STATE)
                ss_final_path = Path(f"temp_ss_{random.randint(1000, 9999)}_final.png")
                await page.screenshot(path=ss_final_path)
                show_ss_callback(ss_final_path) 
                
                log("   ✅ Visit complete. Final preview updated.")
                return
            except PlaywrightError as exc:
                log(f"   ⚠️ attempt {attempt} failed: PlaywrightError: {exc.__class__.__name__}: {str(exc)[:50]}...")
            except Exception as exc:
                log(f"   ⚠️ attempt {attempt} failed: Exception: {exc.__class__.__name__}: {str(exc)[:50]}...")
            finally:
                await context.close()
                
        log("  ✖ Max retries exceeded; skip.")

def _ensure_browsers(log):
    """Memastikan Playwright Chromium terinstal."""
    if not Path.home().exists(): return

    try:
        cache_root = Path.home() / ".cache/ms-playwright"
        if not (cache_root / "chromium").exists():
            log("[INFO] Installing Playwright Chromium …")
            subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        log(f"[WARNING] Playwright install check failed: {e}")


# ==============================
# Runner Orchestration 
# ==============================

async def _pause_with_check(pause_minutes, stop_event, log):
    """Fungsi jeda dengan pengecekan stop event secara berkala."""
    total_pause_seconds = pause_minutes * 60
    sleep_interval = 1 
    
    for elapsed in range(0, total_pause_seconds, sleep_interval):
        if stop_event.is_set():
            log("[INFO] Stop requested during pause. Terminating now.")
            break
        
        remaining = total_pause_seconds - elapsed
        log(f" [PAUSE] Remaining: {remaining // 60}m {remaining % 60}s...")
        await asyncio.sleep(min(sleep_interval, remaining))
        if stop_event.is_set(): break 

async def _runner(config, stop_event, log, show_ss_callback):
    """Runner tunggal untuk Playwright (External Browser Mode)."""
    target, proxy_server, proxy_user, proxy_pass, batch_size, pause_minutes, concurrent_visitors, ua_mode = config
    ua_gen = UserAgent()
    batch_counter = 0
    semaphore = asyncio.Semaphore(concurrent_visitors)
    browser = None
    
    def get_ua(mode):
        # Logika memilih UA: Googlebot atau Random
        return GOOGLEBOT_UA if mode == "Googlebot" else ua_gen.random
    
    try:
        _ensure_browsers(log)
        async with async_playwright() as p:
            # FIX: Menggunakan headless="new" untuk mitigasi deteksi bot yang lebih baik
            browser = await p.chromium.launch(headless=True) 

            while not stop_event.is_set():
                batch_counter += 1
                log("\n" + "="*50)
                log(f" [BROWSER BATCH {batch_counter}] Starting Browser Batch: {batch_size} Visits.")
                
                ip_public_address = await _get_public_ip_via_playwright(browser, proxy_server, proxy_user, proxy_pass)
                log(f" [PROXY IP] Traffic will appear from Public IP: **{ip_public_address}**")
                
                tasks = []
                for i in range(1, batch_size + 1):
                    if stop_event.is_set(): break
                    ua = get_ua(ua_mode)
                    # Meneruskan ua_mode ke _playwright_visit
                    task = asyncio.create_task(_playwright_visit(browser, target, ua, proxy_server, proxy_user, proxy_pass, ip_public_address, log, semaphore, show_ss_callback, ua_mode))
                    tasks.append(task)
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                
                if tasks:
                    log(f"  [CONCURRENT] Awaiting {len(tasks)} visitors to complete (Stop check enabled)...")
                    
                    # Tunggu semua task
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    
                    if stop_event.is_set():
                        log(" [STOP] Cancelling remaining tasks immediately.")
                        for task in pending:
                            task.cancel()
                        break
                    
                    if pending:
                         await asyncio.gather(*pending)
                    
                if stop_event.is_set(): break 

                log(f"\n [BROWSER BATCH {batch_counter}] Batch finished. Pausing for {pause_minutes} minutes...")
                await _pause_with_check(pause_minutes, stop_event, log)
                
            if browser: await browser.close()
    except Exception as e:
        log(f"[FATAL] Browser Runner failed: {e.__class__.__name__}: {e}")
    finally:
        log("[DONE] Browser Injection stopped.")

def _resolve_proxy_ip(proxy_host_port: str) -> str:
    try:
        parts = urlparse(proxy_host_port)
        host = parts.netloc.split(':')[0]
        port = parts.port if parts.port else "80"

        if not host: return proxy_host_port
        return f"{host}:{port}"
    except Exception:
        return proxy_host_port


# ==============================
# GUI Class (CustomTkinter)
# ==============================

class TrafficInjectorTab(ctk.CTkFrame):
    master_ref = None
    reset_gui_callback = None

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        TrafficInjectorTab.master_ref = master
        self.is_running = False
        self.stop_event = threading.Event()
        self.worker_threads = [] 
        self.tk_img = None 
        
        TrafficInjectorTab.reset_gui_callback = self._reset_gui

        # TITLE & INFO
        ctk.CTkLabel(self, text="🚀 Traffic Injector - Playwright Browser Only", 
                     font=("Roboto", 20, "bold")).pack(pady=(10,5))
        ctk.CTkLabel(self, text="Menggunakan Browser External (Playwright) untuk kunjungan realistis.", 
                     text_color="#AAAAAA", wraplength=800).pack(pady=(0,10))

        # INPUT FRAME
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill="x", padx=12, pady=(6,8))
        
        self.entries = {}
        
        # Mode Playwright (Fixed)
        self._create_info_mode(0)
        
        self._create_ua_selection(1) 
        
        self._create_input_field("Target URL", "https://sifani.uinsaizu.ac.id/uni.php", 2)
        self._create_input_field("Proxy Server", "http://proxy.packetstream.io:31112", 3)
        self._create_input_field("Proxy Username", "shiro19", 4)
        self.entries["Proxy Password"] = self._create_input_field("Proxy Password", "bNonWzrlX75xNiB6_country-Indonesia", 5, show="*")
        self._create_input_field("Visits per Batch", "10", 6)
        self._create_input_field("Pause Between Batches (minutes)", "5", 7)
        self._create_input_field("Concurrent Visitors (Slots)", str(CONCURRENT_DEFAULT), 8) 
        
        self.input_frame.grid_columnconfigure(1, weight=1)

        # BUTTON & LOG
        self.start_btn = ctk.CTkButton(self, text="🚀 START CONTINUOUS INJECTION", command=self._on_start, fg_color="#00AA00", hover_color="#00CC00", font=("Roboto", 14, "bold"))
        self.start_btn.pack(fill="x", padx=12, pady=(8, 4))
        self.stop_btn = ctk.CTkButton(self, text="🛑 STOP INJECTION", command=self._on_stop, fg_color="#CC0000", hover_color="#FF3333", font=("Roboto", 14, "bold"), state=tk.DISABLED)
        self.stop_btn.pack(fill="x", padx=12, pady=(0, 4))
        
        # LOG DAN LIVE-PREVIEW SIDE-BY-SIDE
        self.log_preview_frame = ctk.CTkFrame(self, height=450)
        self.log_preview_frame.pack(fill="both", expand=True, padx=12, pady=(4,12))
        self.log_preview_frame.grid_columnconfigure(0, weight=1)
        self.log_preview_frame.grid_columnconfigure(1, weight=0, minsize=MAX_PREVIEW_WIDTH + 20)
        self.log_preview_frame.grid_rowconfigure(0, weight=1)
        self.log_preview_frame.grid_rowconfigure(1, weight=1) # FIX: memastikan baris log bisa di-resize

        # 1. Log Panel (Kiri)
        ctk.CTkLabel(self.log_preview_frame, text="Activity Log:", anchor="w", font=("Roboto", 14, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(10, 5), pady=(10, 2))
        
        # FIX: Memastikan log box mengisi ruang dan scrollable. CTkTextbox sudah punya scrollbar bawaan.
        self.log_box = ctk.CTkTextbox(self.log_preview_frame, font=("Consolas", 11))
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
        self.log_box.configure(state=tk.DISABLED)

        # 2. Live Preview Panel (Kanan)
        ctk.CTkLabel(self.log_preview_frame, text="Live Screenshot Preview (Playwright):", anchor="w", font=("Roboto", 14, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(5, 10), pady=(10, 2))
        
        self.preview_container = ctk.CTkFrame(self.log_preview_frame, width=MAX_PREVIEW_WIDTH, height=MAX_PREVIEW_HEIGHT)
        self.preview_container.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
        self.preview_container.grid_rowconfigure(0, weight=1)
        self.preview_container.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(self.preview_container, text="No Preview Available", text_color="#AAAAAA")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        
    def _create_info_mode(self, row):
        ctk.CTkLabel(self.input_frame, text="Mode Eksekusi:", anchor="w", font=("Roboto", 13, "bold")).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        ctk.CTkLabel(self.input_frame, text="Playwright (Browser External) - Fixed", anchor="w", text_color="#00AAFF").grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        
    def _create_ua_selection(self, row):
        ctk.CTkLabel(self.input_frame, text="User Agent Mode:", anchor="w", font=("Roboto", 13, "bold")).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        
        ua_options = ["Random Browser", "Googlebot"]
        self.ua_var = ctk.StringVar(value=ua_options[0])
        
        ua_combo = ctk.CTkComboBox(self.input_frame, values=ua_options, variable=self.ua_var)
        ua_combo.grid(row=row, column=1, sticky=tk.EW, padx=10, pady=5)
        self.entries["User Agent Mode"] = ua_combo
        
    def _create_input_field(self, label, default="", row=None, show=None):
        ctk.CTkLabel(self.input_frame, text=f"{label}:", anchor="w").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        e = ctk.CTkEntry(self.input_frame, placeholder_text=default, show=show, width=400)
        e.insert(0, default)
        e.grid(row=row, column=1, sticky=tk.EW, padx=10, pady=5)
        self.entries[label] = e
        return e

    def log(self, msg):
        self.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_box.configure(state=tk.NORMAL)
        color = "#00FF00" if "✅" in msg or "[DONE]" in msg else "#FF3333" if "⚠️" in msg or "✖" in msg or "❌" in msg or "[FATAL]" in msg else "#FFFFFF"
        self.log_box.insert(tk.END, f"{msg}\n", ("color",))
        self.log_box.tag_config("color", foreground=color)
        self.log_box.see(tk.END) # Auto-scroll ke bawah
        self.log_box.configure(state=tk.DISABLED)
        
    def _show_screenshot(self, img_path: Path):
        """Menampilkan screenshot di panel preview (dipanggil dari thread utama GUI)."""
        try:
            img = Image.open(img_path)
            
            width, height = img.size
            
            # Hitung rasio resize untuk menyesuaikan dengan MAX_PREVIEW dimensi
            ratio = min(MAX_PREVIEW_WIDTH / width, MAX_PREVIEW_HEIGHT / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(img_resized) # Simpan referensi

            # Update label di panel preview
            self.preview_label.configure(image=self.tk_img, text="")
            
        except FileNotFoundError:
            self.preview_label.configure(text=f"Error: Screenshot file not found.")
        except Exception as e:
            self.preview_label.configure(text=f"Error loading image: {e.__class__.__name__}")
        finally:
            # Hapus file setelah ditampilkan
            img_path.unlink(missing_ok=True)
            
    def _clean_proxy_server(self, server_url: str) -> str:
        if server_url.startswith("http://") or server_url.startswith("https://"):
            return server_url
        return "http://" + server_url
        
    def _clean_target_url(self, url: str) -> str:
        if not url.startswith("http"):
            return "https://" + url
        return url

    def _reset_gui(self, log_msg=""):
        if log_msg: self.log(log_msg)
        
        # Reset Preview Panel
        self.after(0, self.preview_label.configure, {"image": None, "text": "No Preview Available"})
        self.tk_img = None
        
        self.is_running = False
        self.stop_event.clear()
        self.worker_threads = []
        self.start_btn.configure(state=tk.NORMAL, fg_color="#00AA00", text="🚀 START CONTINUOUS INJECTION")
        self.stop_btn.configure(state=tk.DISABLED)

    def _on_stop(self):
        if self.is_running:
            self.log("[USER] 🛑 FORCE STOP SIGNAL SENT! Shutting down all runners...")
            self.stop_event.set()
            self.stop_btn.configure(text="Stopping...", state=tk.DISABLED, fg_color="#FF6666")
        else:
            self.log("[INFO] Tool is not running.")

    def _on_start(self):
        if self.is_running:
            messagebox.showinfo("Running", "Traffic injector sudah berjalan.")
            return

        try:
            proxy_server_raw = self.entries["Proxy Server"].get().strip()
            proxy_user = self.entries["Proxy Username"].get().strip()
            proxy_pass = self.entries["Proxy Password"].get().strip()
            target = self.entries["Target URL"].get().strip()
            batch_size = int(self.entries["Visits per Batch"].get().strip())
            pause_minutes = int(self.entries["Pause Between Batches (minutes)"].get().strip())
            concurrent_visitors = int(self.entries["Concurrent Visitors (Slots)"].get().strip())
            ua_mode = self.ua_var.get()
        except ValueError:
            messagebox.showerror("Input Error", "Semua nilai numerik harus berupa angka.")
            return

        if not proxy_server_raw or not target:
            messagebox.showerror("Input Error", "Proxy Server dan Target URL wajib diisi.")
            return
        
        target_clean = self._clean_target_url(target)
        proxy_server_clean = self._clean_proxy_server(proxy_server_raw)
        proxy_server_log = _resolve_proxy_ip(proxy_server_clean)

        self.is_running = True
        self.stop_event.clear()
        self.worker_threads = []
        self.start_btn.configure(state=tk.DISABLED, text="🚀 RUNNING BROWSER INJECTION...", fg_color="#333333")
        self.stop_btn.configure(state=tk.NORMAL)
        
        config_data = (target_clean, proxy_server_clean, proxy_user, proxy_pass, batch_size, pause_minutes, concurrent_visitors, ua_mode)

        self.log("\n" + "="*50)
        self.log(f"[INFO] Started Browser-Only Injection (Playwright).")
        self.log(f"[INFO] Target: {target_clean} | Proxy Host: {proxy_server_log}")
        self.log(f"[INFO] UA Mode: **{ua_mode}** | Batch Size: {batch_size} | Concurrent: {concurrent_visitors}")

        # MEMBUAT WORKER THREAD TUNGGAL
        def worker():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.log(f"[THREAD] Starting Playwright Runner...")
                
                show_ss_callback = lambda p: self.after(0, self._show_screenshot, p)
                loop.run_until_complete(_runner(config_data, self.stop_event, self.log, show_ss_callback))

            except Exception as e:
                self.log(f"[FATAL THREAD] Playwright thread failed: {e.__class__.__name__}")
            finally:
                self._check_all_threads_finished()


        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self.worker_threads.append(thread)

    def _check_all_threads_finished(self):
        """Memeriksa apakah semua thread worker sudah selesai."""
        def check():
            if not self.is_running:
                return

            alive_threads = [t for t in self.worker_threads if t.is_alive()]
            
            if not alive_threads:
                self.after(0, self._reset_gui, "[INFO] All injection processes successfully terminated.")
            else:
                self.after(1000, check)
        
        self.after(100, check)

if __name__ == "__main__":
    try:
        app = ctk.CTk()
        app.title("SEO Injector Dashboard (Playwright Only)")
        app.geometry("1000x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        sidebar_frame = ctk.CTkFrame(app, width=140, corner_radius=0)
        sidebar_frame.pack(fill="y", side="left")
        ctk.CTkLabel(sidebar_frame, text="User Dashboard", font=("Roboto", 16)).pack(pady=20, padx=20)
        
        ctk.CTkButton(sidebar_frame, text="Traffic Injector").pack(pady=10)

        main_tab = TrafficInjectorTab(app)
        main_tab.pack(side="right", fill="both", expand=True)

        app.mainloop()
    except Exception as e:
        print(f"FATAL GUI ERROR: {e}")