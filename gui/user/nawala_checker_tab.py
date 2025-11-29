import os
import json
import asyncio
import aiohttp
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog, messagebox
from urllib.parse import urlparse, parse_qs


BLOCK_HOST_KEYWORDS = [
    "nawala", "trustpositif", "internetpositif", "kominfo",
    "blokir", "internetbaik", "telkomsel", "safesearch", "block"
]
BLOCK_BODY_KEYWORDS = [
    "internet positif", "internetpositif", "nawala", "site blocked",
    "blocked by", "domain is blocked"
]


def ensure_results_dir():
    path = os.path.join(os.getcwd(), "results")
    os.makedirs(path, exist_ok=True)
    return path


def normalize_url(domain: str) -> str:
    d = domain.strip()
    if not d.startswith(("http://", "https://")):
        d = "http://" + d
    return d


def _is_block_host(host: str) -> bool:
    return any(k in host.lower() for k in BLOCK_HOST_KEYWORDS if host)


def _body_indicates_block(body: str) -> bool:
    return any(k in body.lower() for k in BLOCK_BODY_KEYWORDS if body)


async def check_domain(session: aiohttp.ClientSession, url: str) -> dict:
    try:
        async with session.get(url, timeout=12, allow_redirects=True) as resp:
            final = str(resp.url)
            status = resp.status
            parsed = urlparse(final)
            host = parsed.netloc or ""
            query = parse_qs(parsed.query)
            body = await resp.text(errors="ignore")

            orig_url = None
            for k in ("orig_url", "url", "target", "u"):
                if k in query and query[k]:
                    orig_url = query[k][0]
                    break

            blocked_by_host = _is_block_host(host)
            blocked_by_body = _body_indicates_block(body)
            blocked = blocked_by_host or blocked_by_body

            reason_parts = []
            if blocked_by_host:
                reason_parts.append(f"redirect_host={host}")
            if blocked_by_body:
                reason_parts.append("body_keyword_match")
            if orig_url:
                reason_parts.append(f"orig_url={orig_url}")
            reason = "; ".join(reason_parts) if reason_parts else "accessible"

            return {
                "url": url,
                "status": status,
                "final_url": final,
                "blocked": blocked,
                "reason": reason
            }
    except asyncio.TimeoutError:
        return {"url": url, "status": "Timeout", "blocked": True, "reason": "Timeout"}
    except Exception as e:
        return {"url": url, "status": "Error", "blocked": True, "reason": str(e)}


async def run_check(domains: list, progress_callback=None, update_stats=None):
    results = []
    conn = aiohttp.TCPConnector(limit_per_host=20, ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [check_domain(session, normalize_url(d)) for d in domains]
        total = len(tasks)
        done = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            done += 1
            if progress_callback:
                progress_callback(result)
            if update_stats:
                update_stats(done, total, result)
    return results


class NawalaCheckerTab(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.results = []
        self.stats = {"ok": 0, "blocked": 0, "error": 0, "total": 0}

        ctk.CTkLabel(self, text="🧱 Nawala / Internet Positif Checker",
                     font=("Roboto", 22, "bold")).pack(pady=(12, 4))
        ctk.CTkLabel(self, text="Deteksi redirect ke halaman blokir seperti InternetBaik / Kominfo.",
                     font=("Roboto", 13), text_color="#AAAAAA").pack(pady=(0, 8))

        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=15, pady=(4, 10))
        self.entry = ctk.CTkEntry(top, placeholder_text="Masukkan domain", width=450)
        self.entry.pack(side="left", padx=(10, 6), pady=8)
        ctk.CTkButton(top, text="Cek Single", command=self.check_single).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Cek File .txt", command=self.load_file).pack(side="left", padx=4)

        self.output_box = ctk.CTkTextbox(self, height=380, width=950, font=("Consolas", 11))
        self.output_box.pack(fill="both", expand=True, padx=15, pady=(0, 8))
        self._log(">> Ready for checking domains...\n", "white")

        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(self, variable=self.progress_var, width=600)
        self.progress_bar.pack(pady=(0, 5))

        self.stats_label = ctk.CTkLabel(self, text="Total: 0 | 🟢 OK: 0 | 🔴 Blocked: 0 | ⚠ Error: 0",
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
        self.stats = {"ok": 0, "blocked": 0, "error": 0, "total": 0}
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", header + "\n")
        self.output_box.configure(state="disabled")
        self._update_stats_label()

    def _update_stats_label(self):
        s = self.stats
        txt = f"Total: {s['total']} | 🟢 OK: {s['ok']} | 🔴 Blocked: {s['blocked']} | ⚠ Error: {s['error']}"
        self.stats_label.configure(text=txt)

    def _update_stats(self, done, total, res):
        self.stats["total"] = total
        if res.get("blocked"):
            if res["status"] in ("Error", "Timeout"):
                self.stats["error"] += 1
            else:
                self.stats["blocked"] += 1
        else:
            self.stats["ok"] += 1
        self._update_stats_label()
        self.progress_var.set(done / total)

    def check_single(self):
        d = self.entry.get().strip()
        if not d:
            messagebox.showwarning("Input", "Masukkan domain dulu bro.")
            return
        self._reset_output(f">> Checking: {d}")
        asyncio.run(self._run_async([d]))

    def load_file(self):
        path = filedialog.askopenfilename(title="Pilih file domain", filetypes=[("Text Files", "*.txt")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            domains = [x.strip() for x in f if x.strip()]
        if not domains:
            messagebox.showwarning("Kosong", "File kosong bro.")
            return
        self._reset_output(f">> Checking {len(domains)} domains from {os.path.basename(path)}")
        asyncio.run(self._run_async(domains))

    async def _run_async(self, domains):
        self._log(">> Starting async scanning...\n", "white")

        def on_progress(r):
            url, st, reason = r["url"], r["status"], r.get("reason", "")
            if r["blocked"]:
                self._log(f"[🔴 BLOCKED] {url} -> {st} | {reason}", "red")
            else:
                self._log(f"[🟢 OK] {url} -> {st} | {reason}", "green")

        results = await run_check(domains, progress_callback=on_progress, update_stats=self._update_stats)
        self.results = results
        self._log("\n>> ✅ Scan selesai. Simpan hasil bila perlu.\n", "white")

    def save_results(self):
        if not self.results:
            messagebox.showwarning("Kosong", "Belum ada hasil untuk disimpan.")
            return
        folder = ensure_results_dir()
        filename = datetime.now().strftime("%Y%m%d_%H%M%S_nawala.json")
        path = os.path.join(folder, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Saved", f"Hasil disimpan di:\n{path}")
