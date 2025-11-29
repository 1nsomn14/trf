"""
gui/login_window.py
"""

import os, traceback, customtkinter as ctk
from tkinter import filedialog, messagebox
from core.auth_tools import validate_admin_login, validate_user_login, ROOT as ROOT_DIR

PRIVATE_KEY_PATH = os.path.join(ROOT_DIR, "private_key.pem")

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.geometry("560x520")
        self.title("🔐 Login - SEO Injector Tools")

        self.input_method = ctk.StringVar(value="token")
        self.pub_path = None

        ctk.CTkLabel(self, text="🚀 SEO Injector Tools", font=("Roboto", 20, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="Login User", font=("Roboto", 14)).pack()

        ctk.CTkLabel(self, text="Username").pack(anchor="w", padx=40)
        self.username = ctk.CTkEntry(self, width=360); self.username.pack(pady=4)

        ctk.CTkLabel(self, text="Metode Login").pack(anchor="w", padx=40)
        frame = ctk.CTkFrame(self); frame.pack(fill="x", padx=40, pady=4)
        ctk.CTkRadioButton(frame, text="Paste Token", variable=self.input_method, value="token", command=self.toggle_method).pack(side="left", padx=6)
        ctk.CTkRadioButton(frame, text="Upload File Public Key", variable=self.input_method, value="file", command=self.toggle_method).pack(side="left", padx=6)

        self.label_token = ctk.CTkLabel(self, text="License Token")
        self.label_token.pack(anchor="w", padx=40)
        self.token_box = ctk.CTkTextbox(self, height=100, width=520)
        self.token_box.pack(pady=6)

        self.btn_upload = ctk.CTkButton(self, text="📂 Upload Public Key", command=self.upload_file)
        self.lbl_file = ctk.CTkLabel(self, text="Belum ada file dipilih.")

        ctk.CTkButton(self, text="Login", command=self.login_action).pack(pady=10)
        ctk.CTkButton(self, text="🔑 Admin Login", command=self.login_admin).pack(pady=4)

    # ==============================
    # Toggle Input Method
    # ==============================
    def toggle_method(self):
        if self.input_method.get() == "token":
            if not self.token_box.winfo_ismapped():
                self.label_token.pack(anchor="w", padx=40)
                self.token_box.pack(pady=6)
            if self.btn_upload.winfo_ismapped():
                self.btn_upload.pack_forget(); self.lbl_file.pack_forget()
        else:
            if self.token_box.winfo_ismapped():
                self.label_token.pack_forget(); self.token_box.pack_forget()
            if not self.btn_upload.winfo_ismapped():
                self.btn_upload.pack(pady=6); self.lbl_file.pack()

    # ==============================
    # Upload File
    # ==============================
    def upload_file(self):
        path = filedialog.askopenfilename(title="Pilih File Public Key", filetypes=[("PEM files", "*.pem")])
        if path:
            self.pub_path = os.path.abspath(path)
            self.lbl_file.configure(text=os.path.basename(path))

    # ==============================
    # Admin Login
    # ==============================
    def login_admin(self):
        if not os.path.exists(PRIVATE_KEY_PATH):
            messagebox.showwarning("Admin", "private_key.pem tidak ditemukan di root folder.")
            return
        if validate_admin_login():
            messagebox.showinfo("Login", "Selamat datang Admin!")
            from gui.admin.admin_main import AdminMain 
            self.destroy()
            app = AdminMain()
            app.mainloop()
        else:
            messagebox.showerror("Gagal", "private_key.pem tidak valid.")

    # ==============================
    # User Login
    # ==============================
    def login_action(self):
        uname = self.username.get().strip()
        token = self.token_box.get("1.0", "end").strip() if self.input_method.get() == "token" else None
        try:
            session = validate_user_login(uname, token, self.pub_path)
            from gui.user.user_dashboard import UserDashboard   
            self.destroy()
            dash = UserDashboard(session)
            dash.mainloop()
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Login Gagal", str(e))
