# gui/user/domain_filter_tab.py
import os
import threading
import asyncio
import customtkinter as ctk
from tkinter import messagebox
from core.dom_filter_core import process_files_async, get_domlist_files, format_count

class DomainFilterTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="#0f0f17")
        self.filters = ["kabupaten","kota","prov","instansi","akademik","gov","edu","ac"]
        self.file_vars = {}
        self.filter_vars = {}
        self.running = False
        self._build_ui()
        self._load_files()

    def _build_ui(self):
        ctk.CTkLabel(self, text="🌐 Domain Filter", font=("Consolas",18,"bold"), text_color="#00ADB5").pack(pady=(12,6))
        top = ctk.CTkFrame(self, fg_color="#081018")
        top.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(top, text="Threads:", text_color="#c8c8c8").grid(row=0,column=0,padx=6,pady=8,sticky="w")
        self.threads_var = ctk.StringVar(value="4")
        ctk.CTkEntry(top, width=80, textvariable=self.threads_var).grid(row=0,column=1,padx=6,pady=8,sticky="w")

        container = ctk.CTkFrame(self, fg_color="#07101a")
        container.pack(fill="both", expand=True, padx=12, pady=(6,12))
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(container, fg_color="#061017")
        left.grid(row=0,column=0,sticky="nsew",padx=8,pady=8)
        ctk.CTkLabel(left, text="📂 Files (domlist/)", text_color="#c8c8c8").pack(pady=6)
        self.file_scroll = ctk.CTkScrollableFrame(left, fg_color="#061017")
        self.file_scroll.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkButton(left, text="Refresh", command=self._load_files).pack(pady=6)

        right = ctk.CTkFrame(container, fg_color="#061017")
        right.grid(row=0,column=1,sticky="nsew",padx=8,pady=8)
        ctk.CTkLabel(right, text="🎯 Filters", text_color="#c8c8c8").pack(pady=6)
        self.filter_scroll = ctk.CTkScrollableFrame(right, fg_color="#061017")
        self.filter_scroll.pack(fill="both", expand=True, padx=8, pady=8)
        for f in self.filters:
            var = ctk.BooleanVar(value=False)
            self.filter_vars[f] = var
            ctk.CTkCheckBox(self.filter_scroll, text=f, variable=var).pack(anchor="w",padx=8,pady=3)

        bottom = ctk.CTkFrame(self, fg_color="#071017")
        bottom.pack(fill="x", padx=12, pady=(6,12))
        ctk.CTkLabel(bottom, text="Output name:", text_color="#c8c8c8").grid(row=0,column=0,padx=8,pady=8,sticky="w")
        self.output_entry = ctk.CTkEntry(bottom, width=320)
        self.output_entry.grid(row=0,column=1,padx=8,pady=8,sticky="w")
        self.run_btn = ctk.CTkButton(bottom, text="🚀 Run", fg_color="#2f9e44", command=self._run)
        self.run_btn.grid(row=0,column=2,padx=8,pady=8)
        self.status = ctk.CTkLabel(bottom, text="Status: Idle", text_color="#c8c8c8")
        self.status.grid(row=1,column=0,columnspan=3,sticky="w",padx=8,pady=(4,8))

        log_box = ctk.CTkFrame(self, fg_color="#06121a")
        log_box.pack(fill="both", padx=12, pady=(0,12), expand=True)
        ctk.CTkLabel(log_box, text="Activity Log", text_color="#9be7ff").pack(anchor="w", padx=8, pady=(8,2))
        self.log_text = ctk.CTkTextbox(log_box, height=200, fg_color="#05050a", text_color="#00FF9C")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        self._clear_log()
        self.log("Ready.")

    def _load_files(self):
        for w in self.file_scroll.winfo_children():
            w.destroy()
        self.file_vars = {}
        for f in get_domlist_files():
            var = ctk.BooleanVar(value=False)
            self.file_vars[f] = var
            ctk.CTkCheckBox(self.file_scroll, text=os.path.basename(f), variable=var).pack(anchor="w",padx=8,pady=3)

    def _log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.yview_moveto(1.0)
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _run(self):
        if self.running: return
        self._clear_log()
        files = [f for f,v in self.file_vars.items() if v.get()]
        filters = [k for k,v in self.filter_vars.items() if v.get()]
        custom = (self.output_entry.get() or "").strip()  
        if not files:
            self.log("❌ No files selected.")
            return
        if not filters:
            self.log("❌ No filters selected.")
            return
        try:
            threads = max(1, int(self.threads_var.get()))
        except Exception:
            threads = 4
        outname = self.output_entry.get().strip() or "hasil_filter.txt"
        self.running = True
        self.run_btn.configure(state="disabled")
        self.status.configure(text=f"Status: Running ({len(files)} files)...")
        self.log(f"Starting async filter — files: {len(files)} | filters: {', '.join(filters)} | concurrency: {threads}")

        def progress_cb(done, total, matched):
            self.log(f"Progress: {done}/{total} — total {format_count(matched)}")

        async def runner():
            await process_files_async(files, filters, outname, concurrency=threads, buffer_limit=8000, progress_cb=progress_cb)

        def thread_target():
            try:
                asyncio.run(runner())
                self.log("✅ Done. All files processed.")
            except Exception as e:
                self.log(f"❌ Error: {e}")
            finally:
                self.running = False
                self.run_btn.configure(state="normal")
                self.status.configure(text="Status: Idle")

        threading.Thread(target=thread_target, daemon=True).start()

    def log(self, msg):
        self._log(msg)
