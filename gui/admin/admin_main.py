# gui/admin/admin_main.py
import customtkinter as ctk
from core.admin_tools import ensure_paths
from gui.admin.admin_docs_viewer import AdminDocsViewer
from gui.admin.admin_docs_editor import AdminDocsEditor
from gui.admin.admin_license_tools import AdminLicenseTools
from gui.admin.admin_history_viewer import AdminHistoryViewer
from gui.admin.admin_user_manager import AdminUserManager
from tkinter import messagebox

class AdminMain(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Admin Dashboard — SEO Injector")
        self.geometry("1200x740")

        ensure_paths()

        self.sidebar = ctk.CTkFrame(self, width=260)
        self.sidebar.pack(side="left", fill="y")
        self.content = ctk.CTkFrame(self)
        self.content.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(self.sidebar, text="🛠 Admin Panel", font=("Roboto", 20, "bold")).pack(pady=(20, 8))

        ctk.CTkButton(self.sidebar, text="📘 Docs Viewer", command=self.show_docs).pack(padx=12, pady=6, fill="x")
        ctk.CTkButton(self.sidebar, text="✏️ Edit Docs", command=self.open_editor).pack(padx=12, pady=6, fill="x")
        ctk.CTkButton(self.sidebar, text="🔑 License Tools", command=self.show_license).pack(padx=12, pady=6, fill="x")
        ctk.CTkButton(self.sidebar, text="🗂 License History", command=self.show_history).pack(padx=12, pady=6, fill="x")
        ctk.CTkButton(self.sidebar, text="👥 Users", command=self.show_users).pack(padx=12, pady=6, fill="x")

        ctk.CTkButton(self.sidebar, text="🚪 Logout", command=self.logout, fg_color="#8B0000").pack(padx=12, pady=20, fill="x")

        self.current = None
        self.show_docs()

    def _mount(self, frame_cls):
        if self.current:
            self.current.destroy()
        self.current = frame_cls(self.content)
        self.current.pack(fill="both", expand=True, padx=8, pady=8)

    def show_docs(self):
        self._mount(AdminDocsViewer)

    def open_editor(self):
        def refresh_after_save():
            if isinstance(self.current, AdminDocsViewer):
                self.current.refresh_view()
        AdminDocsEditor(self, on_save_callback=refresh_after_save)

    def show_license(self):
        self._mount(AdminLicenseTools)

    def show_history(self):
        self._mount(AdminHistoryViewer)

    def show_users(self):
        self._mount(AdminUserManager)

    def logout(self):
        messagebox.showinfo("Logout", "Berhasil logout dari Admin Panel.")
        from gui.login_window import LoginWindow  
        self.destroy()
        app = LoginWindow()
        app.mainloop()

if __name__ == "__main__":
    app = AdminMain()
    app.mainloop()
