"""
gui/user/popup_warning.py — FULL
"""

import customtkinter as ctk

def feature_locked_popup(parent, feature_name: str):
    win = ctk.CTkToplevel(parent)
    win.title("Fitur Terkunci 🔒")
    win.geometry("420x190")
    win.grab_set()
    ctk.CTkLabel(win, text="🚫 Akses Ditolak", font=("Roboto", 18, "bold"), text_color="#FF4D4D").pack(pady=(18, 4))
    ctk.CTkLabel(
        win,
        text=f"Fitur '{feature_name}' belum aktif di lisensi kamu.\nHubungi admin untuk upgrade.",
        font=("Roboto", 13),
        text_color="#EEEEEE",
        justify="center"
    ).pack(pady=(0, 14))
    ctk.CTkButton(win, text="Tutup", command=win.destroy, width=120).pack()
