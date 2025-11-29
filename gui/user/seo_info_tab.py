import customtkinter as ctk
from tkinter import messagebox
from core.seo_api import get_seo_info, save_seo_snapshot, get_seo_history
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class SEOInfoTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)

        ctk.CTkLabel(self, text="🔍 SEO Info Checker", font=("Roboto", 18, "bold")).pack(pady=(14, 6))

        top_row = ctk.CTkFrame(self)
        top_row.pack(fill="x", pady=(4, 8), padx=12)
        self.entry_domain = ctk.CTkEntry(top_row, placeholder_text="contoh: google.com", width=300)
        self.entry_domain.pack(side="left", padx=(0, 8))
        self.btn_check = ctk.CTkButton(top_row, text="Cek Sekarang", command=self.check_seo)
        self.btn_check.pack(side="left")

        self.metric_var = ctk.StringVar(value="pages_crawled_from_root_domain")
        metric_frame = ctk.CTkFrame(self)
        metric_frame.pack(fill="x", padx=12, pady=(6, 10))
        ctk.CTkLabel(metric_frame, text="Metric Chart:").pack(side="left", padx=(4, 6))
        for label, key in [
            ("Pages Crawled", "pages_crawled_from_root_domain"),
            ("Root Domains", "root_domains_to_root_domain"),
            ("External Pages", "external_pages_to_root_domain"),
            ("Deleted Pages", "deleted_pages_to_root_domain"),
            ("Redirect Pages", "redirect_pages_to_page"),
        ]:
            ctk.CTkRadioButton(metric_frame, text=label, variable=self.metric_var, value=key,
                               command=self._on_metric_change).pack(side="left", padx=4)

        self.result_frame = ctk.CTkScrollableFrame(self)
        self.result_frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        self._chart_canvas = None
        self._chart_fig = None

    def check_seo(self):
        domain = self.entry_domain.get().strip()
        if not domain:
            messagebox.showwarning("Input", "Isi domain dulu bro.")
            return

        for w in self.result_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.result_frame, text=f"⏳ Mengambil data SEO untuk {domain}...",
                     font=("Roboto", 13, "italic")).pack(pady=8)

        data = get_seo_info(domain)
        for w in self.result_frame.winfo_children():
            w.destroy()

        if isinstance(data, dict) and data.get("error"):
            ctk.CTkLabel(self.result_frame, text=f"⚠️ Error: {data['error']}", text_color="red").pack(pady=8)
            return

        try:
            save_seo_snapshot(domain, data)
        except Exception:
            pass

        history = get_seo_history(domain, 2)
        prev_data = history[0]["data"] if len(history) >= 2 else {}

        self.display_summary(data, prev_data)

        hist = get_seo_history(domain, 30)
        self.plot_history_chart(hist, self.metric_var.get(), f"{domain} - 30 Hari")

        self.display_full_table(data, prev_data)

    def display_summary(self, info: dict, prev: dict):
        SectionTitle(self.result_frame, "🌐 Domain Summary")
        InfoRow(self.result_frame, "Domain", info.get("root_domain", "N/A"))
        InfoRow(self.result_frame, "Page", info.get("page", "N/A"))
        InfoRow(self.result_frame, "Last Crawled", info.get("last_crawled", "N/A"))
        InfoRow(self.result_frame, "HTTP Code", info.get("http_code", "N/A"))

        SectionTitle(self.result_frame, "📊 Authority Metrics (with Trend)")
        CardGrid(self.result_frame, {
            "Domain Authority": (info.get("domain_authority", 0), prev.get("domain_authority")),
            "Page Authority": (info.get("page_authority", 0), prev.get("page_authority")),
            "Spam Score": (info.get("spam_score", 0), prev.get("spam_score")),
            "Root Domains": (info.get("root_domains_to_root_domain", 0), prev.get("root_domains_to_root_domain")),
            "Pages Crawled": (info.get("pages_crawled_from_root_domain", 0), prev.get("pages_crawled_from_root_domain"))
        })

    def plot_history_chart(self, history, metric, title):
        if self._chart_canvas:
            try:
                self._chart_canvas.get_tk_widget().destroy()
                plt.close(self._chart_fig)
            except Exception:
                pass

        dates, values = [], []
        for entry in history:
            dates.append(entry.get("date"))
            val = entry.get("data", {}).get(metric, 0)
            try:
                values.append(int(float(val)))
            except Exception:
                values.append(0)

        if not dates:
            ctk.CTkLabel(self.result_frame,
                         text="(Belum ada data history — akan disimpan otomatis setelah cek pertama)",
                         text_color="#BBBBBB").pack(pady=8)
            return

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(8, 3.2))
        ax.plot(dates, values, marker="o", linewidth=2, color="#00ADB5")
        ax.set_title(title, color="#00ADB5")
        ax.tick_params(axis="x", rotation=40, colors="white")
        ax.tick_params(axis="y", colors="white")

        if values:
            ax.annotate(fmt_km(values[-1]),
                        xy=(len(dates) - 1, values[-1]),
                        xytext=(0, 8),
                        textcoords="offset points",
                        color="#EEEEEE")
        fig.tight_layout()

        self._chart_fig = fig
        canvas = FigureCanvasTkAgg(fig, master=self.result_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=12)
        self._chart_canvas = canvas

    def display_full_table(self, info: dict, prev: dict):
        SectionTitle(self.result_frame, "📋 Detailed SEO Metrics (Clean & Trend)")

        groups = {
            "🌍 Domain Info": ["page", "subdomain", "root_domain", "title", "last_crawled", "http_code"],
            "🔗 Link Metrics - Page": [k for k in info.keys() if "_to_page" in k],
            "🕸️ Link Metrics - Subdomain": [k for k in info.keys() if "_to_subdomain" in k],
            "🧩 Link Metrics - Root Domain": [k for k in info.keys() if "_to_root_domain" in k and not k.startswith("external_")],
            "🌐 External Link Data": [k for k in info.keys() if k.startswith("external_")],
            "📊 Authority & Quality": ["page_authority", "domain_authority", "link_propensity", "spam_score"],
            "🧠 Outbound Data": [k for k in info.keys() if "_from_" in k],
            "🧾 Crawled Stats": [k for k in info.keys() if "crawled" in k or "deleted" in k],
        }

        for title, keys in groups.items():
            valid_keys = [k for k in keys if k in info]
            if not valid_keys:
                continue

            sec = ctk.CTkFrame(self.result_frame, fg_color="#1A1A1A", corner_radius=8)
            sec.pack(fill="x", padx=8, pady=(8, 10))
            ctk.CTkLabel(sec, text=title, font=("Roboto", 14, "bold"), text_color="#00ADB5").pack(anchor="w", padx=12, pady=6)

            grid = ctk.CTkFrame(sec, fg_color="#222831", corner_radius=8)
            grid.pack(fill="x", padx=10, pady=(4, 8))

            row, col = 0, 0
            for key in valid_keys:
                val = info.get(key, "—")
                prev_val = prev.get(key, None)
                formatted = fmt_km(val) if is_number(val) else str(val)
                trend_txt, trend_color = get_trend(val, prev_val)

                color_val = "#EEEEEE"
                if key == "spam_score":
                    try:
                        score = float(val)
                        color_val = "#FF4D4D" if score >= 5 else "#3CD070"
                    except Exception:
                        pass

                item = ctk.CTkFrame(grid, fg_color="transparent")
                item.grid(row=row, column=col, sticky="ew", padx=10, pady=3)

                ctk.CTkLabel(item, text=key.replace("_", " ").title(),
                             text_color="#BBBBBB", font=("Roboto", 12, "bold"),
                             width=300, anchor="w").pack(side="left", padx=(4, 4), pady=2)

                frame_val = ctk.CTkFrame(item, fg_color="transparent")
                frame_val.pack(side="right")
                ctk.CTkLabel(frame_val, text=formatted, text_color=color_val,
                             font=("Consolas", 12, "bold"), anchor="e", width=70).pack(side="left")
                if trend_txt:
                    ctk.CTkLabel(frame_val, text=f" {trend_txt}", text_color=trend_color,
                                 font=("Roboto", 11, "bold")).pack(side="left")

                if col == 0:
                    col = 1
                else:
                    col = 0
                    row += 1

    def _on_metric_change(self):
        domain = self.entry_domain.get().strip()
        if not domain:
            return
        hist = get_seo_history(domain, 30)
        self.plot_history_chart(hist, self.metric_var.get(), f"{domain} - 30 Hari")


def is_number(val):
    try:
        float(val)
        return True
    except Exception:
        return False


def fmt_km(val):
    try:
        num = float(val)
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        else:
            return f"{int(num)}"
    except Exception:
        return str(val)


def get_trend(curr, prev):
    try:
        curr, prev = float(curr), float(prev)
        if prev == 0:
            return "", "#BBBBBB"
        diff = ((curr - prev) / prev) * 100
        if diff > 0:
            return f"↑ {diff:.1f}%", "#3CD070"
        elif diff < 0:
            return f"↓ {abs(diff):.1f}%", "#FF4D4D"
        else:
            return "=", "#BBBBBB"
    except Exception:
        return "", "#BBBBBB"


class SectionTitle(ctk.CTkFrame):
    def __init__(self, parent, text):
        super().__init__(parent, fg_color="#222831", corner_radius=8)
        self.pack(fill="x", pady=(12, 4), padx=6)
        ctk.CTkLabel(self, text=text, font=("Roboto", 15, "bold"),
                     text_color="#00ADB5").pack(anchor="w", padx=10, pady=6)


class InfoRow(ctk.CTkFrame):
    def __init__(self, parent, key, value):
        super().__init__(parent, fg_color="#1A1A1A", corner_radius=8)
        self.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(self, text=key, font=("Roboto", 13, "bold"),
                     width=260, anchor="w").pack(side="left", padx=10, pady=5)
        ctk.CTkLabel(self, text=value, font=("Roboto", 13),
                     text_color="#EEEEEE", anchor="w").pack(side="left", padx=10)


class CardGrid(ctk.CTkFrame):
    def __init__(self, parent, data: dict):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x", pady=(4, 10))
        for i, (k, vals) in enumerate(data.items()):
            curr, prev = vals if isinstance(vals, tuple) else (vals, None)
            color = "#EEEEEE"

            if k.lower() == "spam score":
                try:
                    val = float(curr)
                    color = "#FF4D4D" if val >= 5 else "#3CD070"
                except Exception:
                    pass

            trend_txt, trend_color = get_trend(curr, prev)

            card = ctk.CTkFrame(self, fg_color="#222831", corner_radius=10)
            card.grid(row=0, column=i, padx=8, pady=6, sticky="nsew")

            ctk.CTkLabel(card, text=k, text_color="#BBBBBB",
                         font=("Roboto", 12, "bold")).pack(padx=10, pady=(8, 0))

            val_frame = ctk.CTkFrame(card, fg_color="transparent")
            val_frame.pack()

            ctk.CTkLabel(val_frame, text=fmt_km(curr), font=("Roboto", 16, "bold"),
                         text_color=color).pack(side="left")

            if trend_txt:
                ctk.CTkLabel(val_frame, text=f" {trend_txt}", text_color=trend_color,
                             font=("Roboto", 11, "bold")).pack(side="left")
