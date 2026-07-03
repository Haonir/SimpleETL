import sys
import os

# Fix imports for both PyInstaller and normal execution
if getattr(sys, 'frozen', False):
    # PyInstaller sets sys.frozen attribute
    sys.path.insert(0, os.path.dirname(sys.executable))

try:
    from .main_ui import SimpleETLApp
except ImportError:
    from core.main_ui import SimpleETLApp

import customtkinter as ctk


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = SimpleETLApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()