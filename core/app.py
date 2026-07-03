"""Entry point for PyInstaller"""
import customtkinter as ctk
from core.main_ui import SimpleETLApp

def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = SimpleETLApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
