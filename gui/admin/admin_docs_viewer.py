# gui/admin/admin_docs_viewer.py
import os
import customtkinter as ctk
from tkhtmlview import HTMLLabel
import markdown

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC_PATH = os.path.join(BASE_DIR, "assets", "docs", "admin_doc.md")

class AdminDocsViewer(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        ctk.CTkLabel(
            self,
            text="📘 Admin Documentation",
            font=("Roboto", 18, "bold")
        ).pack(pady=(8, 4))
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkButton(btn_frame, text="🔄 Refresh", command=self.refresh_view).pack(side="left", padx=8)

        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=8, pady=8)

        self.html_label = HTMLLabel(self.scroll, html="", width=100)
        self.html_label.pack(fill="both", expand=True)

        self.refresh_view()

    def refresh_view(self):
        if not os.path.exists(DOC_PATH):
            self.html_label.set_html("<h3 style='color:red;'>❌ File admin_doc.md tidak ditemukan.</h3>")
            return

        with open(DOC_PATH, "r", encoding="utf-8") as f:
            md_text = f.read()

        html = markdown.markdown(md_text, extensions=["extra", "tables"])
        self.html_label.set_html(
            f"<div style='font-family:Roboto,Arial; line-height:1.6; padding:12px; color:black;'>{html}</div>"
        )
