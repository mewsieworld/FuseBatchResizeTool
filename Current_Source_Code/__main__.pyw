import tkinter as tk
from resizer_app import ImageResizerApp
from utils import resource_path
import sys

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
        root.iconbitmap(resource_path("mewsiepto.ico"))
    except Exception as e:
        print(f"[Warning] Failed to load icon: {e}")
    app = ImageResizerApp(root)
    root.mainloop()
