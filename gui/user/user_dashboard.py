import customtkinter as ctk
from tkinter import messagebox
from gui.user.seo_info_tab import SEOInfoTab
from gui.user.popup_warning import feature_locked_popup
from gui.user.nawala_checker_tab import NawalaCheckerTab
from gui.user.broken_link_checker_tab import BrokenLinkCheckerTab
from gui.user.user_web_destroyer import SlotReporterUI
from gui.user.traffic_injector_tab import TrafficInjectorTab
from gui.user.hacking_dashboard_tab import HackingDashboardTab 

class UserDashboard(ctk.CTk):
    def __init__(self, session: dict):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.geometry("1200x720")
        self.title("👤 User Dashboard — SEO Injector")

        self.username = session.get("username", "")
        self.features = session.get("features", []) or []
        self.claims = session.get("claims", {}) or {}

        # ==============================
        # Layout utama
        # ==============================
        self.sidebar = ctk.CTkFrame(self, width=240)
        self.sidebar.pack(side="left", fill="y")

        self.content = ctk.CTkFrame(self)
        self.content.pack(side="right", fill="both", expand=True)

        # Sidebar Header
        ctk.CTkLabel(
            self.sidebar,
            text="🧰 User Dashboard",
            font=("Roboto", 20, "bold")
        ).pack(pady=(20, 10))

        # ==============================
        # Sidebar Menu
        # ==============================
        self.menu_buttons = {}

        menu_items = [
            ("🏠 Home", "home", self.show_home),
            ("🔍 SEO Info", "seo_info", self.open_seo),
            ("🚀 Traffic Injector", "traffic_injector", self.open_traffic),
            ("🔗 Backlink Injector", "backlink_injector", self.open_backlink),
            ("💣 Web Destroyer", "web_destroyer", self.open_destroyer),
            ("😈 Hacking Dashboard", "hacking_dashboard", self.open_hacking), # <-- TOMBOL BARU DITAMBAHKAN
            ("🧱 Nawala Checker", "nawala_checker", self.open_nawala),
            ("🪤 Broken Link Checker", "broken_link_checker", self.open_broken),
            ("🚧 Coming Soon", "coming_soon", self.open_coming),
            ("🚪 Logout", "logout", self.logout),
        ]

        for text, feature, cmd in menu_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                anchor="w",
                width=220,
                height=38,
                command=lambda f=feature, c=cmd: self._gate_and_open(f, c)
            )
            btn.pack(padx=10, pady=4, fill="x")
            self.menu_buttons[feature] = btn

        # ==============================
        # Default halaman Home
        # ==============================
        self.current_frame = None
        self.show_home()

    # =====================================================
    # Helper mount frame
    # =====================================================
    def _mount(self, frame: ctk.CTkFrame):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame
        self.current_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # =====================================================
    # Gating fitur (lisensi)
    # =====================================================
    def _gate_and_open(self, feature, callback):
        if feature in ["home", "coming_soon", "logout", "web_reporter"]:  
            callback()
            return
        if "*" in self.features or feature in self.features:
            callback()
        else:
            feature_locked_popup(self, feature)

    # =====================================================
    # HOME PAGE
    # =====================================================
    def show_home(self):
        frame = ctk.CTkFrame(self.content)

        ctk.CTkLabel(frame, text="👋 Selamat Datang di SEO Injector Tools!", font=("Roboto", 20, "bold")).pack(pady=(10, 5))
        ctk.CTkLabel(frame, text=f"User aktif: {self.username}", font=("Roboto", 14)).pack(pady=4)

        # Info user
        info_box = ctk.CTkFrame(frame)
        info_box.pack(padx=12, pady=10, fill="x")

        exp = self.claims.get("exp", "—")
        license_type = self.claims.get("type", "User")
        features = self.features if self.features else ["Tidak ada fitur aktif"]

        ctk.CTkLabel(info_box, text="📋 Informasi Lisensi", font=("Roboto", 15, "bold")).pack(pady=(6, 4))
        ctk.CTkLabel(info_box, text=f"License Type: {license_type}", font=("Roboto", 13)).pack(pady=2)
        ctk.CTkLabel(info_box, text=f"Expired: {exp}", font=("Roboto", 13)).pack(pady=2)
        ctk.CTkLabel(info_box, text=f"Fitur Aktif: {', '.join(features)}", font=("Roboto", 13)).pack(pady=2)

        # Docs section
        doc_box = ctk.CTkFrame(frame)
        doc_box.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        ctk.CTkLabel(doc_box, text="📘 Panduan Penggunaan", font=("Roboto", 15, "bold")).pack(pady=(8, 4))
        doc_text = (
            "✨ Gunakan tools sesuai fitur yang aktif di akun kamu.\n\n"
            "🔍 SEO Info: Analisa domain (DA, PA, Spam Score, dll)\n"
            "🚀 Traffic Injector: Analisa & simulasi traffic domain\n"
            "🔗 Backlink Injector: Tambahkan backlink otomatis (dummy mode)\n"
            "💣 Web Destroyer: Testing stress load atau exploit (simulasi)\n"
            "😈 Hacking Dashboard: Tools untuk serangan tingkat lanjut (stress testing, dll)\n" # <-- UPDATE PANDUAN
            "🧱 Nawala Checker: Deteksi domain yang diblokir\n"
            "🪤 Broken Link Checker: Temukan link rusak di websitemu\n"
            "🚧 Coming Soon: Preview fitur yang akan datang!\n\n"
            "Jika fitur terkunci 🔒, hubungi admin untuk upgrade lisensi."
        )
        lbl_doc = ctk.CTkTextbox(doc_box, width=800, height=220)
        lbl_doc.pack(padx=10, pady=10)
        lbl_doc.insert("1.0", doc_text)
        lbl_doc.configure(state="disabled")

        self._mount(frame)

    # =====================================================
    # SEO INFO
    # =====================================================
    def open_seo(self):
        frame = ctk.CTkFrame(self.content)
        SEOInfoTab(frame).pack(fill="both", expand=True)
        self._mount(frame)

    # =====================================================
    # TRAFFIC INJECTOR
    # =====================================================
    def open_traffic(self):
        frame = ctk.CTkFrame(self.content)
        TrafficInjectorTab(frame).pack(fill="both", expand=True) 
        self._mount(frame)
        
    # =====================================================
    # HACKING DASHBOARD (BARU)
    # =====================================================
    def open_hacking(self):
        frame = ctk.CTkFrame(self.content)
        HackingDashboardTab(frame).pack(fill="both", expand=True) 
        self._mount(frame)

    # =====================================================
    # BACKLINK INJECTOR
    # =====================================================
    def open_backlink(self):
        frame = ctk.CTkFrame(self.content)
        ctk.CTkLabel(frame, text="🔗 Backlink Injector", font=("Roboto", 18, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(frame, text="Tambahkan backlink otomatis untuk meningkatkan DA/PA.", font=("Roboto", 13)).pack(pady=5)
        ctk.CTkLabel(frame, text="(Fitur akan hadir di update berikutnya 🚀)", text_color="#AAAAAA").pack(pady=20)
        self._mount(frame)

    # =====================================================
    # WEB DESTROYER
    # =====================================================
    def open_destroyer(self):
        frame = ctk.CTkFrame(self.content)
        SlotReporterUI(frame).pack(fill="both", expand=True)
        self._mount(frame)

    # =====================================================
    # NAWALA CHECKER
    # =====================================================
    def open_nawala(self):
        frame = ctk.CTkFrame(self.content)
        NawalaCheckerTab(frame).pack(fill="both", expand=True)
        self._mount(frame)


    # =====================================================
    # BROKEN LINK CHECKER
    # =====================================================
    def open_broken(self):
        frame = ctk.CTkFrame(self.content)
        BrokenLinkCheckerTab(frame).pack(fill="both", expand=True)
        self._mount(frame)


    # =====================================================
    # COMING SOON
    # =====================================================
    def open_coming(self):
        frame = ctk.CTkFrame(self.content)
        ctk.CTkLabel(frame, text="🚧 Coming Soon Features", font=("Roboto", 18, "bold")).pack(pady=(15, 10))
        features_upcoming = [
            "💣 Update engine web destroyer",
            "📈 Keyword suggestion",
            "📧 Auto generate sitemap",
            "💉 Backlink Injector"
        ]
        for feat in features_upcoming:
            ctk.CTkLabel(frame, text=feat, font=("Roboto", 13), text_color="#CCCCCC").pack(anchor="w", padx=30, pady=4)
        ctk.CTkLabel(frame, text="Stay tuned for the next update! 🚀", text_color="#00ADB5").pack(pady=20)
        self._mount(frame)

    # =====================================================
    # LOGOUT
    # =====================================================
    def logout(self):
        messagebox.showinfo("Logout", "Berhasil logout dari User Dashboard.")
        from gui.login_window import LoginWindow
        self.destroy()
        app = LoginWindow()
        app.mainloop()


if __name__ == "__main__":
    dummy = {
        "username": "demo_user",
        "features": ["seo_info", "traffic_injector", "web_destroyer", "nawala_checker", "broken_link_checker", "hacking_dashboard"], 
        "claims": {"type": "Premium", "exp": "2026-01-01"}
    }
    import time
    app = UserDashboard(dummy)
    app.mainloop()