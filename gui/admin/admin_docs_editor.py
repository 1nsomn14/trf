# gui/admin/admin_docs_editor.py
import os
import customtkinter as ctk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC_PATH = os.path.join(BASE_DIR, "assets", "docs", "admin_doc.md")
DOCS_BACKUP_DIR = os.path.join(BASE_DIR, "assets", "docs", "backups")

class AdminDocsEditor(ctk.CTkToplevel):

    def __init__(self, master=None, on_save_callback=None):
        super().__init__(master)
        self.title("✏️ Edit Admin Documentation")
        self.geometry("900x600")
        self.on_save_callback = on_save_callback

        self.lift()                    
        self.attributes("-topmost", True)   
        self.after(100, lambda: self.attributes("-topmost", False))  
        self.focus_force()            
        self.grab_set()                

        os.makedirs(DOCS_BACKUP_DIR, exist_ok=True)

        self.textbox = ctk.CTkTextbox(self, wrap="word")
        self.textbox.pack(fill="both", expand=True, padx=8, pady=8)

        self._load_markdown_file()

        ctk.CTkButton(
            self, text="💾 Save & Close", command=self._save_and_close
        ).pack(pady=10)

    def _load_markdown_file(self):

        if not os.path.exists(DOC_PATH):
            self.textbox.insert(
                "1.0",
                "# Admin Documentation\n\nFile belum ada, silakan isi dokumentasi di sini...",
            )
            return
        with open(DOC_PATH, "r", encoding="utf-8") as f:
            md_text = f.read()
            self.textbox.insert("1.0", md_text)

    def _save_and_close(self):

        content = self.textbox.get("1.0", "end").strip()

        import time
        backup_name = f"admin_doc_backup_{time.strftime('%Y%m%d-%H%M%S')}.md"
        backup_path = os.path.join(DOCS_BACKUP_DIR, backup_name)

        try:

            if os.path.exists(DOC_PATH):
                with open(DOC_PATH, "r", encoding="utf-8") as oldf:
                    old_data = oldf.read()
                with open(backup_path, "w", encoding="utf-8") as bf:
                    bf.write(old_data)

            with open(DOC_PATH, "w", encoding="utf-8") as f:
                f.write(content)

            messagebox.showinfo("Saved", f"Dokumentasi berhasil disimpan!\nBackup: {backup_name}")

            if self.on_save_callback:
                self.on_save_callback()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan file:\n{e}")
