import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

class ResolutionPicker(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Resolution Manager")
        self.grab_set()  # Make window modal
        
        # Set window size and position
        self.geometry("300x500")
        self.resizable(True, True)
        self.minsize(300, 400)
        
        # Center window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        # Default resolutions
        self.default_resolutions = [
            "200x200",
            "150x150",
            "100x100",
            "50x50"
        ]

        # Create main frame with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create and pack the resolution list frame
        list_frame = ttk.LabelFrame(main_frame, text="Available Resolutions", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create listbox and scrollbar
        self.listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, 
                                 activestyle='none',  # No underline on active item
                                 selectbackground='#0078D7',  # Windows blue selection color
                                 selectforeground='white')
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)

        # Pack listbox and scrollbar
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind Ctrl+A to select all
        self.listbox.bind('<Control-a>', self.select_all)
        self.bind('<Control-a>', self.select_all)  # Also bind to window

        # Create custom resolution frame
        custom_frame = ttk.LabelFrame(main_frame, text="Add Custom Resolution", padding="5")
        custom_frame.pack(fill=tk.X, pady=(0, 10))

        # Add validation for numeric input
        vcmd = (self.register(self.validate_number), '%P')

        # Width entry
        width_frame = ttk.Frame(custom_frame)
        width_frame.pack(fill=tk.X, pady=2)
        ttk.Label(width_frame, text="Width:").pack(side=tk.LEFT)
        self.width_entry = ttk.Entry(width_frame, width=6, validate='key', validatecommand=vcmd)
        self.width_entry.pack(side=tk.LEFT, padx=5)

        # Height entry
        height_frame = ttk.Frame(custom_frame)
        height_frame.pack(fill=tk.X, pady=2)
        ttk.Label(height_frame, text="Height:").pack(side=tk.LEFT)
        self.height_entry = ttk.Entry(height_frame, width=6, validate='key', validatecommand=vcmd)
        self.height_entry.pack(side=tk.LEFT, padx=5)

        # Add resolution button
        ttk.Button(custom_frame, text="Add Resolution", command=self.add_resolution).pack(fill=tk.X, pady=(5, 0))

        # Create button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))

        # Add buttons
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Select All", command=lambda: self.select_all(None)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Confirm", command=self.confirm).pack(side=tk.RIGHT, padx=5)

        # Right-click menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Delete", command=self.delete_selected)
        self.listbox.bind("<Button-3>", self.show_context_menu)

        # Load saved resolutions or defaults
        self.load_resolutions()

        # Store the result
        self.result = None

    def validate_number(self, value):
        if value == "":
            return True
        try:
            num = int(value)
            return 0 <= num <= 9999
        except ValueError:
            return False

    def add_resolution(self):
        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            
            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be greater than 0")
                return
                
            resolution = f"{width}x{height}"
            
            # Check if resolution already exists
            if resolution not in self.listbox.get(0, tk.END):
                # Store current selections
                current_selections = list(self.listbox.curselection())
                
                # Add new resolution
                self.listbox.insert(tk.END, resolution)
                
                # Restore previous selections
                for index in current_selections:
                    self.listbox.selection_set(index)
                    
                # Select the new resolution
                self.listbox.selection_set(tk.END)
                
                # Clear entries
                self.width_entry.delete(0, tk.END)
                self.height_entry.delete(0, tk.END)
                
                # Save resolutions
                self.save_resolutions()
            else:
                messagebox.showwarning("Warning", "This resolution already exists")
                
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def delete_selected(self):
        selected = self.listbox.curselection()
        if not selected:
            return
            
        # Delete in reverse order to maintain correct indices
        for index in reversed(selected):
            self.listbox.delete(index)
            
        # Save the updated list
        self.save_resolutions()

    def show_context_menu(self, event):
        # Only show menu if clicking on an item
        index = self.listbox.nearest(event.y)
        if index >= 0 and self.listbox.bbox(index):  # Check if item exists and is visible
            # Select the item under the cursor if not already selected
            if index not in self.listbox.curselection():
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(index)
            
            # Show the menu at mouse position
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
        return "break"  # Prevent default right-click behavior

    def load_resolutions(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), "resolution_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    resolutions = json.load(f)
                    if resolutions:
                        for res in resolutions:
                            self.listbox.insert(tk.END, res)
                        return
        except Exception as e:
            print(f"Error loading resolutions: {e}")
            
        # If no saved resolutions or error, load defaults
        for res in self.default_resolutions:
            self.listbox.insert(tk.END, res)

    def save_resolutions(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), "resolution_config.json")
            resolutions = list(self.listbox.get(0, tk.END))
            with open(config_path, 'w') as f:
                json.dump(resolutions, f)
        except Exception as e:
            print(f"Error saving resolutions: {e}")

    def confirm(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "Please select at least one resolution")
            return
            
        self.result = []
        for index in selected:
            resolution = self.listbox.get(index)
            width, height = map(int, resolution.split('x'))
            self.result.append((width, height))
            
        self.save_resolutions()
        self.destroy()

    def select_all(self, event):
        self.listbox.select_set(0, tk.END)
        return "break"  # Prevent default Ctrl+A behavior
