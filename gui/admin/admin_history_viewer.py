# gui/admin/admin_history_viewer.py
import json
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from core.admin_tools import get_license_history

class AdminHistoryViewer(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        ctk.CTkLabel(self, text="🗂 License History", font=("Roboto", 18, "bold")).pack(pady=(8, 6))

        btn_row = ctk.CTkFrame(self)
        btn_row.pack(fill="x", padx=8)
        ctk.CTkButton(btn_row, text="Refresh", command=self.refresh).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Export JSON", command=self.export_json).pack(side="left")

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(table_frame, columns=("ts","user_id","type","features","token_preview"), show="headings", height=14)
        self.tree.heading("ts", text="Timestamp (UTC)")
        self.tree.heading("user_id", text="User ID")
        self.tree.heading("type", text="Type")
        self.tree.heading("features", text="Features")
        self.tree.heading("token_preview", text="Token Preview")

        self.tree.column("ts", width=200, anchor="w")
        self.tree.column("user_id", width=140, anchor="w")
        self.tree.column("type", width=80, anchor="center")
        self.tree.column("features", width=240, anchor="w")
        self.tree.column("token_preview", width=240, anchor="w")
        self.tree.pack(fill="both", expand=True)

        style = ttk.Style(self.tree)
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure("Treeview", rowheight=24)

        self._data_cache = []
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        data = get_license_history(limit=200)
        self._data_cache = data
        for row in data:
            payload = row.get("payload", {})
            _type = payload.get("type", "-")
            feats = payload.get("features", [])
            feats_str = ", ".join(feats) if isinstance(feats, (list, tuple)) else str(feats)
            self.tree.insert(
                "", "end",
                values=(
                    row.get("ts","-"),
                    row.get("user_id","-"),
                    _type,
                    feats_str,
                    row.get("token_preview","-"),
                )
            )

    def export_json(self):
        if not self._data_cache:
            messagebox.showwarning("Export", "Tidak ada data history untuk diexport.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON","*.json"),("All","*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data_cache, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Export", f"Saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
