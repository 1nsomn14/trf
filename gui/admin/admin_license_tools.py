# gui/admin/admin_license_tools.py
import os
import customtkinter as ctk
from tkinter import messagebox, filedialog, Tk

from core.admin_tools import (
    generate_admin_keypair,
    generate_new_user,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS_DIR = os.path.join(BASE_DIR, "assets", "keys")


def copy_to_clipboard(text: str):
    root = Tk()
    root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
    root.destroy()


class AdminLicenseTools(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        os.makedirs(KEYS_DIR, exist_ok=True)

        ctk.CTkLabel(self, text="🔐 User Generator & License Tools", font=("Roboto", 17, "bold")).pack(pady=(10, 6))

        ctk.CTkButton(self, text="Generate Admin Private Key", command=self.do_generate_admin_key).pack(
            padx=12, pady=6, fill="x"
        )

        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(form_frame, text="Username").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.ent_username = ctk.CTkEntry(form_frame)
        self.ent_username.grid(row=0, column=1, sticky="ew", padx=6, pady=6)

        ctk.CTkLabel(form_frame, text="Days Valid").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.ent_days = ctk.CTkEntry(form_frame)
        self.ent_days.insert(0, "365")
        self.ent_days.grid(row=1, column=1, sticky="ew", padx=6, pady=6)

        ctk.CTkLabel(form_frame, text="Features (comma)").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        self.ent_features = ctk.CTkEntry(form_frame)
        self.ent_features.insert(0, "traffic,backlink")
        self.ent_features.grid(row=2, column=1, sticky="ew", padx=6, pady=6)

        form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            self,
            text="🧩 Generate New User",
            command=self.do_generate_user,
            fg_color="#1e90ff"
        ).pack(padx=12, pady=(8, 6), fill="x")

        ctk.CTkButton(
            self,
            text="📋 Copy Token",
            command=self.copy_token
        ).pack(padx=12, pady=(4, 10), fill="x")

        self.output = ctk.CTkTextbox(self, height=260)
        self.output.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # =====================================================
    # ACTIONS
    # =====================================================

    def do_generate_admin_key(self):
        try:
            generate_admin_keypair(overwrite=False)
            messagebox.showinfo("Success", "✅ private_key.pem berhasil dibuat di root project.")
        except FileExistsError:
            if messagebox.askyesno("Overwrite?", "private_key.pem sudah ada. Mau overwrite?"):
                generate_admin_keypair(overwrite=True)
                messagebox.showinfo("Overwritten", "🔄 private_key.pem berhasil diganti.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def do_generate_user(self):
        username = self.ent_username.get().strip()
        days_str = self.ent_days.get().strip() or "365"
        feats = self.ent_features.get().strip()

        if not username:
            messagebox.showwarning("Input", "Isi username dulu bro!")
            return

        try:
            days = int(days_str)
            features = [x.strip() for x in feats.split(",") if x.strip()]
        except ValueError:
            messagebox.showwarning("Input", "Masukkan angka valid untuk Days Valid.")
            return

        try:
            result = generate_new_user(
                username=username,
                license_type="user",
                days_valid=days,
                features=features
            )

            self.output.delete("1.0", "end")
            self.output.insert(
                "1.0",
                f"✅ USER CREATED SUCCESSFULLY ✅\n\n"
                f"User ID   : {result['user_id']}\n"
                f"Username  : {result['username']}\n"
                f"Expires   : {result['expires']}\n"
                f"Public Key: {result['public_key']}\n\n"
                f"License Token:\n{result['license_token']}\n"
            )

            messagebox.showinfo("Success", f"User '{username}' berhasil dibuat!")

        except ValueError as ve:

            messagebox.showwarning("Duplicate", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def copy_token(self):
        token = self.output.get("1.0", "end").strip()
        if not token:
            messagebox.showwarning("Copy", "Tidak ada token untuk disalin.")
            return
        copy_to_clipboard(token)
        messagebox.showinfo("Copied", "Token berhasil disalin ke clipboard.")
