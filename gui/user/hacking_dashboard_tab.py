# gui/user/hacking_dashboard_tab.py
import customtkinter as ctk
from gui.user.domain_filter_tab import DomainFilterTab

class HackingDashboardTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="#0f0f17")
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="😈 Hacking Dashboard", font=("Consolas",20,"bold"), text_color="#FF8C00").pack(pady=12)
        tabs = ctk.CTkTabview(self, width=1000, height=620)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)
        tabs.add("Overview")
        tabs.add("Domain Filter")
        tabs.tab("Overview").configure(fg_color="#12121a")
        ctk.CTkLabel(tabs.tab("Overview"), text="Overview / quick tools", text_color="#c8c8c8").pack(pady=20)
        DomainFilterTab(tabs.tab("Domain Filter")).pack(fill="both", expand=True)
