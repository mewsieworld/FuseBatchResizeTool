import tkinter as tk
from resizer_app import ImageResizerApp
from utils import resource_path # RESTORED
import sys
import os # ADDED

# ADDED user's resource_path function
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundled EXE"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_base_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return os.path.dirname(sys.executable)
    else:
        # Running from .pyw
        return os.path.dirname(__file__)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        # This will now use the resource_path defined in this file
        root.iconbitmap(resource_path("mewsiepto.ico"))
    except Exception as e:
        print(f"[Warning] Failed to load icon: {e}")

    # Load manual_contents
    manual_contents_for_app = None
    try:
        manual_path_val = resource_path("manual.md")
        with open(manual_path_val, "r", encoding="utf-8") as f:
            manual_contents_for_app = f.read()
    except Exception as e:
        print(f"[Error] Failed to load manual.md for app: {e}")
        # manual_contents_for_app remains None

    app = ImageResizerApp(root, manual_contents=manual_contents_for_app) # MODIFIED to pass manual_contents
    root.mainloop()
