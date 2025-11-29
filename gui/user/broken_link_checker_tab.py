import os
import json
import asyncio
import aiohttp
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog, messagebox


def ensure_results_dir():
    path = os.path.join(os.getcwd(), "results")
    os.makedirs(path, exist_ok=True)
    return path


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url


def is_broken(status: int) -> bool:
    try:
        s = int(status)
        return 400 <= s < 600
    except Exception:
        return True


async def check_url(session: aiohttp.ClientSession, url: str) -> dict:
    try:
        async with session.get(url, timeout=10) as resp:
            status = resp.status
            broken = is_broken(status)
            return {"url": url, "status": status, "broken": broken, "reason": "HTTP Error" if broken else "OK"}
    except asyncio.TimeoutError:
        return {"url": url, "status": "Timeout", "broken": True, "reason": "Timeout"}
    except Exception as e:
        return {"url": url, "status": "Error", "broken": True, "reason": str(e)}


async def run_check(urls: list, progress_callback=None, update_stats=None):
    results = []
    conn = aiohttp.TCPConnector(limit_per_host=20, ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [check_url(session, normalize_url(u)) for u in urls]
        total = len(tasks)
        done = 0
        for coro in asyncio.as_completed(tasks):
            res = await coro
            results.append(res)
            done += 1
            if progress_callback:
                progress_callback(res)
            if update_stats:
                update_stats(done, total, res)
    return results


class BrokenLinkCheckerTab(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.results = []
        self.stats = {"ok": 0, "broken": 0, "error": 0, "total": 0}

        ctk.CTkLabel(self, text="🔗 Broken Link Checker", font=("Roboto", 22, "bold")).pack(pady=(12, 4))
        ctk.CTkLabel(self, text="Deteksi link rusak berdasarkan status HTTP.", font=("Roboto", 13),
                     text_color="#AAAAAA").pack(pady=(0, 10))

        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=15, pady=5)

        self.entry = ctk.CTkEntry(input_frame, placeholder_text="Masukkan URL atau domain", width=450)
        self.entry.pack(side="left", padx=(10, 5), pady=10)
        ctk.CTkButton(input_frame, text="Cek Single", command=self.check_single).pack(side="left", padx=4)
        ctk.CTkButton(input_frame, text="Cek File .txt", command=self.load_file).pack(side="left", padx=4)

        self.output_box = ctk.CTkTextbox(self, height=380, width=950, font=("Consolas", 11))
        self.output_box.pack(fill="both", expand=True, padx=15, pady=(0, 8))
        self._log(">> Ready for broken link scan...\n", "white")

        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(self, variable=self.progress_var, width=600)
        self.progress_bar.pack(pady=(0, 5))

        self.stats_label = ctk.CTkLabel(self, text="Total: 0 | 🟢 OK: 0 | 🔴 Broken: 0 | ⚠ Error: 0",
                                        font=("Consolas", 12))
        self.stats_label.pack(pady=(0, 10))

        ctk.CTkButton(self, text="💾 Simpan Hasil (JSON)", command=self.save_results).pack(pady=(0, 10))

    def _log(self, text: str, color="white"):
        self.output_box.configure(state="normal")
        self.output_box.insert("end", text + "\n")
        self.output_box.tag_config("red", foreground="#FF5555")
        self.output_box.tag_config("green", foreground="#00FF7F")
        self.output_box.tag_config("white", foreground="#DDDDDD")
        self.output_box.tag_add(color, "end-2l", "end-1l")
        self.output_box.see("end")
        self.output_box.configure(state="disabled")

    def _reset_output(self, header: str):
        self.results.clear()
        self.stats = {"ok": 0, "broken": 0, "error": 0, "total": 0}
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", header + "\n")
        self.output_box.configure(state="disabled")
        self._update_stats_label()

    def _update_stats_label(self):
        s = self.stats
        self.stats_label.configure(
            text=f"Total: {s['total']} | 🟢 OK: {s['ok']} | 🔴 Broken: {s['broken']} | ⚠ Error: {s['error']}"
        )

    def _update_stats(self, done, total, res):
        self.stats["total"] = total
        if res.get("broken"):
            if res["status"] in ("Error", "Timeout"):
                self.stats["error"] += 1
            else:
                self.stats["broken"] += 1
        else:
            self.stats["ok"] += 1
        self._update_stats_label()
        self.progress_var.set(done / total)

    def check_single(self):
        url = self.entry.get().strip()
        if not url:
            messagebox.showwarning("Input", "Masukkan URL dulu bro!")
            return
        self._reset_output(f">> Checking single URL: {url}")
        asyncio.run(self._run_async([url]))

    def load_file(self):
        path = filedialog.askopenfilename(title="Pilih file URL list", filetypes=[("Text Files", "*.txt")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            urls = [u.strip() for u in f if u.strip()]
        if not urls:
            messagebox.showwarning("Kosong", "File tidak berisi URL bro.")
            return
        self._reset_output(f">> Checking {len(urls)} URLs from file: {os.path.basename(path)}")
        asyncio.run(self._run_async(urls))

    async def _run_async(self, urls):
        self._log(">> Starting async Broken Link check...\n", "white")

        def on_progress(r):
            url, st, reason = r["url"], r["status"], r.get("reason", "")
            if r["broken"]:
                self._log(f"[🔴 BROKEN] {url} -> {st} | {reason}", "red")
            else:
                self._log(f"[🟢 OK] {url} -> {st} | {reason}", "green")

        results = await run_check(urls, progress_callback=on_progress, update_stats=self._update_stats)
        self.results = results
        self._log("\n>> ✅ Scan selesai. Klik 'Simpan Hasil' untuk export JSON.\n", "white")

    def save_results(self):
        if not self.results:
            messagebox.showwarning("Kosong", "Belum ada hasil untuk disimpan.")
            return
        folder = ensure_results_dir()
        filename = datetime.now().strftime("%Y%m%d_%H%M%S_broken.json")
        path = os.path.join(folder, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Saved", f"Hasil disimpan di:\n{path}")
