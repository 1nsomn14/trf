import os
import json
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog, Tk
from core.admin_tools import update_user_features, get_user_features

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
USERS_PATH = os.path.join(BASE_DIR, "data", "users.json")
KEYS_DIR = os.path.join(BASE_DIR, "assets", "keys")

def copy_to_clipboard(text: str):
    root = Tk()
    root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
    root.destroy()

class AdminUserManager(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        ctk.CTkLabel(self, text="👥 User Management", font=("Roboto", 20, "bold")).pack(pady=(10, 5))

        btn_row = ctk.CTkFrame(self)
        btn_row.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkButton(btn_row, text="🔄 Refresh", command=self.load_users).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="⚙️ Edit Features", command=self.open_edit_features).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="💾 Export JSON", command=self.export_json).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="🗑 Delete User", fg_color="#8B0000", command=self.delete_user).pack(side="left")

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=8, pady=(6, 8))

        columns = ("user_id", "username", "license_type", "features", "exp", "public_key_path")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        headers = {
            "user_id": "User ID",
            "username": "Username",
            "license_type": "Type",
            "features": "Features",
            "exp": "Expires",
            "public_key_path": "Public Key Path"
        }

        for col, text in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, anchor="w", width=180)

        self.tree.column("features", width=260)
        self.tree.column("exp", width=160)
        self.tree.column("public_key_path", width=320)
        self.tree.pack(fill="both", expand=True, pady=5)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        style = ttk.Style(self.tree)
        style.theme_use("default")
        style.configure("Treeview", background="#20242A", fieldbackground="#20242A",
                        foreground="#DADADA", rowheight=26, font=("Consolas", 10), borderwidth=0)
        style.configure("Treeview.Heading", font=("Roboto", 11, "bold"),
                        background="#2D323B", foreground="#00BFFF")
        style.map("Treeview", background=[("selected", "#1E90FF")], foreground=[("selected", "white")])

        self.tree.bind("<Double-1>", self.on_double_click)

        self.status_label = ctk.CTkLabel(self, text="", font=("Roboto", 11))
        self.status_label.pack(pady=(2, 4))

        self.load_users()

    def load_users(self):
        self.tree.delete(*self.tree.get_children())

        if not os.path.exists(USERS_PATH):
            self.status_label.configure(text="⚠️ Tidak ada file data/users.json")
            return

        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception:
            users = []

        if not users:
            self.status_label.configure(text="⚠️ Tidak ada user yang tersimpan.")
            return

        for u in users:
            self.tree.insert(
                "",
                "end",
                values=(
                    u.get("user_id", "-"),
                    u.get("username", "-"),
                    u.get("license_type", "-"),
                    ", ".join(u.get("features", [])),
                    u.get("exp", "-"),
                    u.get("public_key_path", "-"),
                )
            )

        self.status_label.configure(text=f"✅ {len(users)} user ditemukan.")

    def delete_user(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Delete", "Pilih user dulu bro.")
            return

        item = self.tree.item(selected[0])
        username = item["values"][1]

        confirm = messagebox.askyesno("Konfirmasi", f"Hapus user '{username}'?")
        if not confirm:
            return

        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                users = json.load(f)

            updated = [u for u in users if u.get("username") != username]

            with open(USERS_PATH, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)

            key_path = os.path.join(KEYS_DIR, f"{username}_public_key.pem")
            if os.path.exists(key_path):
                os.remove(key_path)

            messagebox.showinfo("Deleted", f"User '{username}' berhasil dihapus.")
            self.load_users()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_json(self):
        if not os.path.exists(USERS_PATH):
            messagebox.showwarning("Export", "Belum ada data user untuk diexport.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All Files", "*.*")],
            initialfile="users_export.json",
        )
        if not save_path:
            return

        try:
            with open(USERS_PATH, "r", encoding="utf-8") as src, open(save_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
            messagebox.showinfo("Export", f"Data user berhasil diexport ke:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return

        username = self.tree.item(item[0])["values"][1]
        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                users = json.load(f)
            user_data = next((u for u in users if u.get("username") == username), None)
            if not user_data:
                messagebox.showwarning("Info", "Data user tidak ditemukan.")
                return
            self.show_user_detail(user_data)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_user_detail(self, user_data: dict):
        win = ctk.CTkToplevel(self)
        win.title(f"Detail User: {user_data.get('username')}")
        win.geometry("600x480")
        win.grab_set()

        ctk.CTkLabel(win, text=f"👤 Detail User - {user_data.get('username')}",
                     font=("Roboto", 18, "bold")).pack(pady=(10, 10))

        frame = ctk.CTkFrame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        details = [
            ("User ID", user_data.get("user_id")),
            ("Username", user_data.get("username")),
            ("License Type", user_data.get("license_type")),
            ("Features", ", ".join(user_data.get("features", []))),
            ("Expires", user_data.get("exp")),
            ("Public Key Path", user_data.get("public_key_path")),
        ]

        for i, (label, value) in enumerate(details):
            ctk.CTkLabel(frame, text=f"{label}:", anchor="w").grid(row=i, column=0, sticky="w", padx=8, pady=5)
            ctk.CTkLabel(frame, text=value or "-", anchor="w").grid(row=i, column=1, sticky="w", padx=8, pady=5)

        ctk.CTkLabel(win, text="🔑 License Token Preview", font=("Roboto", 14, "bold")).pack(pady=(8, 2))
        token_box = ctk.CTkTextbox(win, height=120)
        token_box.pack(fill="both", expand=False, padx=12, pady=(0, 8))
        token_box.insert("1.0", user_data.get("token_preview", "No token preview available"))
        token_box.configure(state="disabled")

        ctk.CTkButton(win, text="📋 Copy Token Preview",
                      command=lambda: copy_to_clipboard(user_data.get("token_preview", ""))).pack(pady=(4, 10))

    def open_edit_features(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Edit", "Pilih user dulu bro.")
            return

        item = self.tree.item(selected[0])
        username = item["values"][1]
        current = set(get_user_features(username))

        features_available = [
            "seo_info",
            "traffic_injector",
            "backlink_injector",
            "web_destroyer",
            "nawala_checker",
            "broken_link_checker",
            "hacking_dashboard"
        ]

        popup = ctk.CTkToplevel(self)
        popup.title(f"Edit Features — {username}")
        popup.geometry("400x360")
        popup.grab_set()

        ctk.CTkLabel(popup, text=f"✏️ Edit Fitur untuk {username}",
                     font=("Roboto", 16, "bold")).pack(pady=(12, 8))

        frame = ctk.CTkFrame(popup)
        frame.pack(fill="both", expand=True, padx=12, pady=10)

        vars_ = {}
        for feat in features_available:
            var = ctk.BooleanVar(value=(feat in current))
            ctk.CTkCheckBox(frame, text=feat, variable=var).pack(anchor="w", pady=4, padx=12)
            vars_[feat] = var

        def save():
            new_feats = [k for k, v in vars_.items() if v.get()]
            if update_user_features(username, new_feats):
                messagebox.showinfo("Sukses", f"Fitur '{username}' diperbarui:\n{', '.join(new_feats) if new_feats else '(kosong)'}")
                popup.destroy()
                self.load_users()
            else:
                messagebox.showerror("Error", "Gagal memperbarui fitur.")

        ctk.CTkButton(popup, text="💾 Simpan", command=save).pack(pady=10)
