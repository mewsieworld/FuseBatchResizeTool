import tkinter as tk
from tkinter import messagebox

class ResolutionPicker(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Resolution")

        self.selection = tk.StringVar(value="none")

        tk.Radiobutton(self, text="200x200", variable=self.selection, value="200x200").pack(anchor="w")
        tk.Radiobutton(self, text="150x150", variable=self.selection, value="150x150").pack(anchor="w")
        tk.Radiobutton(self, text="100x100", variable=self.selection, value="100x100").pack(anchor="w")
        tk.Radiobutton(self, text="50x50", variable=self.selection, value="50x50").pack(anchor="w")

        self.custom_frame = tk.Frame(self)
        self.custom_radio = tk.Radiobutton(self.custom_frame, text="Custom", variable=self.selection, value="custom", command=self.toggle_custom_entries)
        self.custom_radio.pack(side="left")
        
        # Add validation function
        def validate_digits(P):
            if P == "":
                return True
            if len(P) > 4:
                return False
            return P.isdigit()
        
        vcmd = (self.register(validate_digits), '%P')
        self.custom_width = tk.Entry(self.custom_frame, width=5, state="disabled", validate="key", validatecommand=vcmd)
        self.custom_width.pack(side="left")
        self.custom_height = tk.Entry(self.custom_frame, width=5, state="disabled", validate="key", validatecommand=vcmd)
        self.custom_height.pack(side="left")
        self.custom_frame.pack(anchor="w")

        tk.Button(self, text="Confirm", command=self.confirm).pack(pady=10)

        self.result = None
        self.grab_set()
        self.focus_set()
        self.transient(parent)

        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        min_width = 250
        min_height = 200
        if width < min_width:
            width = min_width
        if height < min_height:
            height = min_height
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def toggle_custom_entries(self):
        state = "normal" if self.selection.get() == "custom" else "disabled"
        self.custom_width.config(state=state)
        self.custom_height.config(state=state)

    def confirm(self):
        choice = self.selection.get()
        if choice == "200x200":
            self.result = (200, 200)
        elif choice == "150x150":
            self.result = (150, 150)
        elif choice == "100x100":
            self.result = (100, 100)
        elif choice == "50x50":
            self.result = (50, 50)
        elif choice == "custom":
            try:
                width = int(self.custom_width.get())
                height = int(self.custom_height.get())
                if width <= 0 or height <= 0:
                    raise ValueError("Size must be greater than 0")
                self.result = (width, height)
            except ValueError as e:
                if str(e) == "Size must be greater than 0":
                    messagebox.showerror("Error", "Size must be greater than 0")
                else:
                    messagebox.showerror("Error", "Please enter valid numbers for custom size")
                return
        else:
            messagebox.showerror("Error", "noooo wait you gotta select one!")
            return

        self.destroy()
