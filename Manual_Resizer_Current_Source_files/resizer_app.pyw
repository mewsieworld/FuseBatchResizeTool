import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import subprocess
from datetime import datetime
import webbrowser

from utils import rgb_to_hex, resource_path
from resolution_picker import ResolutionPicker
from config import TARGET_SIZE, OUTPUT_FOLDER, SHOW_BG_COLOR_BOX, BG_COLOR_BOX_POSITION

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)

class ImageResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Manual Center Image Resizer")

        # Set minimum window size to accommodate dialog titles
        self.root.minsize(400, 300)  # Set minimum width to 400 pixels

        # (1) Try setting icon
        try:
            self.root.iconbitmap(resource_path("mewsiepto.ico"))
        except Exception as e:
            print(f"[Warning] Failed to load icon: {e}")
    
        # (2) Initialize basic variables
        self.preview_mode_var = tk.StringVar(value="Off")
        self.image_paths = []
        self.base_folder = ""
        self.base_path = get_base_path()
        self.current_index = 0
        self.current_image = None
        self.tk_image = None
        self.display_image = None
        self.bg_color = (255, 0, 255)  # <-- Important: before using rgb_to_hex!
        self.last_output_path = None
        self.left_click_mode = "center"
        self.right_click_mode = "background"
        self.preview_window = None
        self.eyedropper_active = False
        self.show_hex_in_label = False
        self.bg_color_box_position = BG_COLOR_BOX_POSITION
        self.bg_color_toggle_var = tk.BooleanVar(value=SHOW_BG_COLOR_BOX)

        # (3) Setup BG Color Label
        self.bg_color_label = tk.Label(
            root, 
            text="BG Color", 
            width=10, 
            bg=rgb_to_hex(self.bg_color)
        )
        self.bg_color_label.bind("<Button-1>", self.activate_eyedropper)

        # (4) Setup Canvas
        self.canvas = tk.Canvas(root, bg="gray")
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        # (5) Setup Key Binds
        root.bind("<Right>", self.next_image)
        root.bind("<Left>", self.prev_image)
        root.bind("<Escape>", self.cancel_eyedropper)

        # (6) Initialize UI elements
        self.toggle_bg_color_box(init=True)
        self.adjust_frames()

        # (7) Build Menus and Start
        self.create_menu()
        self.update_menu_states()
        self.ask_target_size()
        self.load_images()

    def create_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="📁 Open Folder", command=self.load_images)
        file_menu.add_command(label="🖼️ Set Resolution", command=self.ask_target_size)
        file_menu.add_command(label="🚪 Exit", command=self.root.quit)
        menubar.add_cascade(label="🗂️ File", menu=file_menu)

        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="🖱️ Mouse Mode", command=self.mouse_mode_dialog)

        preview_mode_menu = tk.Menu(options_menu, tearoff=0)
        preview_mode_menu.add_radiobutton(label="🔲 Off", variable=self.preview_mode_var, value="Off")
        preview_mode_menu.add_radiobutton(label="🖼️ Show Last Output", variable=self.preview_mode_var, value="Show Last Output")
        preview_mode_menu.add_radiobutton(label="🔍 Show Crop Preview", variable=self.preview_mode_var, value="Show Crop Preview")
        options_menu.add_cascade(label="🎞️ Preview Mode", menu=preview_mode_menu)

        # Store the bg_color_menu as an instance variable
        self.bg_color_menu = tk.Menu(options_menu, tearoff=0)
        self.bg_color_menu.add_checkbutton(label="🖌️ Toggle BG Color Box", variable=self.bg_color_toggle_var, command=self.toggle_bg_color_box)
        self.bg_color_menu.add_command(label="🎨 Toggle Hex Color", command=self.toggle_hex_label)
        self.bg_color_menu.add_command(label="📏 Change Location", command=self.bg_color_position_dialog)
        options_menu.add_cascade(label="🎨 BG Color Box Options", menu=self.bg_color_menu)

        menubar.add_cascade(label="⚙️ Options", menu=options_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="❓ About", command=self.open_about_window)
        menubar.add_cascade(label="❓ Help", menu=help_menu)

        self.root.config(menu=menubar)
        self.update_menu_states()  # Update menu states after menu creation

    def toggle_hex_label(self):
        self.show_hex_in_label = not self.show_hex_in_label
        self.update_bg_color_label()

    def update_bg_color_label(self):
        if self.show_hex_in_label:
            self.bg_color_label.config(text=rgb_to_hex(self.bg_color))
        else:
            self.bg_color_label.config(text="BG Color")

    def open_about_window(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("400x200")
        about_window.resizable(False, False)

        tk.Label(about_window, text="Manual Center Image Resizer", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(about_window, text="Created for easy manual center-based image cropping and resizing.", wraplength=380, justify="center").pack(pady=5)

        link = tk.Label(about_window, text="GitHub Repository", fg="blue", cursor="hand2")
        link.pack(pady=10)
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/mewsieworld/TO-Fuse-Tools-And-Guides/tree/main/scripts/FuseBatchResizeTool"))

        tk.Button(about_window, text="Close", command=about_window.destroy).pack(pady=10)

    def mouse_mode_dialog(self):
        self.mouse_window = tk.Toplevel(self.root)
        self.mouse_window.title("Mouse Mode")
        self.mouse_window.grab_set()
        self.mouse_window.focus_force()

        self.mode_label = tk.Label(self.mouse_window, text=self.get_mouse_mode_text(), font=("Arial", 14))
        self.mode_label.pack(pady=10)

        button_frame = tk.Frame(self.mouse_window)
        button_frame.pack()

        left_button = tk.Button(button_frame, text="<", command=self.switch_mouse_mode)
        left_button.pack(side=tk.LEFT, padx=10)

        right_button = tk.Button(button_frame, text=">", command=self.switch_mouse_mode)
        right_button.pack(side=tk.LEFT, padx=10)

        ok_button = tk.Button(self.mouse_window, text="OK", command=self.mouse_window.destroy)
        ok_button.pack(pady=10)

    def get_mouse_mode_text(self):
        return f"Left: {self.left_click_mode.capitalize()} | Right: {self.right_click_mode.capitalize()}"

    def switch_mouse_mode(self):
        # Flip left and right click behavior
        if self.left_click_mode == "center":
            self.left_click_mode = "background"
            self.right_click_mode = "center"
        else:
            self.left_click_mode = "center"
            self.right_click_mode = "background"

        # Update the text on the mouse mode popup if it's open
        if hasattr(self, 'mode_label') and self.mode_label.winfo_exists():
            self.mode_label.config(text=self.get_mouse_mode_text())
            
    def activate_eyedropper(self, event=None):
        self.eyedropper_active = True
        self.root.title("Manual Center Image Resizer [Eyedropper Active]")
        self.bg_color_label.config(text="🎯 Pick Color", bg="yellow")

    def cancel_eyedropper(self, event=None):
        if self.eyedropper_active:
            self.eyedropper_active = False
            self.root.title("Manual Center Image Resizer")
            self.bg_color_label.config(bg=rgb_to_hex(self.bg_color))
            self.update_bg_color_label()
            
    def ask_target_size(self):
        global TARGET_SIZE
        picker = ResolutionPicker(self.root)
        self.root.wait_window(picker)
        if picker.result:
            TARGET_SIZE = picker.result
            # Ensure window is wide enough after setting resolution
            self.root.update_idletasks()
            current_width = self.root.winfo_width()
            if current_width < 400:
                self.root.geometry(f"400x{self.root.winfo_height()}")
        else:
            self.root.quit()

    def load_images(self):
        self.base_folder = filedialog.askdirectory(title="Select Folder of Images")
        if not self.base_folder:
            self.root.quit()

        use_timestamp = messagebox.askyesno("New Output Subfolder", "Do you want to create a timestamped output folder inside 'output_resized'?")

        base_output = os.path.join(self.base_path, "output_resized")
        os.makedirs(base_output, exist_ok=True)

        if use_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_folder = os.path.join(base_output, timestamp)
        else:
            self.output_folder = base_output

        os.makedirs(self.output_folder, exist_ok=True)

        self.image_paths = []
        for root_dir, _, files in os.walk(self.base_folder):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    self.image_paths.append(os.path.join(root_dir, file))

        if not self.image_paths:
            messagebox.showerror("Error", "No images found.")
            self.root.quit()

        self.current_index = 0
        self.show_image()
        # Ensure window is wide enough after loading images
        self.root.update_idletasks()
        current_width = self.root.winfo_width()
        if current_width < 400:
            self.root.geometry(f"400x{self.root.winfo_height()}")

    def show_image(self):
        if not self.image_paths:
            return
        img_path = self.image_paths[self.current_index]
        self.current_image = Image.open(img_path).convert("RGB")

        self.display_image = self.current_image.copy()

        screen_width = self.root.winfo_screenwidth() - 100
        screen_height = self.root.winfo_screenheight() - 100
        max_display_size = (screen_width, screen_height)

        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.ANTIALIAS

        self.display_image.thumbnail(max_display_size, resample_filter)

        self.tk_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.delete("all")

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        self.image_x = (canvas_w - self.tk_image.width()) // 2
        self.image_y = (canvas_h - self.tk_image.height()) // 2

        self.canvas.config(width=self.tk_image.width(), height=self.tk_image.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        self.root.geometry("")

    def correct_coordinates(self, event):
        x = event.x
        y = event.y
        return x, y

    def on_left_click(self, event):
        x, y = self.correct_coordinates(event)
        if self.eyedropper_active:
            self.pick_bg_color(x, y)
            return

        if self.left_click_mode == "center":
            self.handle_center_click(x, y)
        elif self.left_click_mode == "background":
            self.handle_background_click(x, y)

    def on_right_click(self, event):
        x, y = self.correct_coordinates(event)
        if self.eyedropper_active:
            self.pick_bg_color(x, y)
            return

        if self.right_click_mode == "background":
            self.handle_background_click(x, y)
        elif self.right_click_mode == "center":
            self.handle_center_click(x, y)

    def pick_bg_color(self, x, y):
        disp_w, disp_h = self.tk_image.width(), self.tk_image.height()
        orig_w, orig_h = self.current_image.size
        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h
        img_x = int(x * scale_x)
        img_y = int(y * scale_y)
        if 0 <= img_x < orig_w and 0 <= img_y < orig_h:
            self.bg_color = self.current_image.getpixel((img_x, img_y))
            self.bg_color_label.config(bg=rgb_to_hex(self.bg_color))
            self.update_bg_color_label()
        self.eyedropper_active = False
        self.root.title("Manual Center Image Resizer")

    def handle_center_click(self, x, y):
        disp_w, disp_h = self.tk_image.width(), self.tk_image.height()
        orig_w, orig_h = self.current_image.size
        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h
        center_x = int(x * scale_x)
        center_y = int(y * scale_y)

        self.process_image(center_x, center_y)

        if self.preview_mode_var.get() == "Show Last Output" and self.last_output_path:
            try:
                subprocess.Popen(["explorer", self.last_output_path], shell=True)
            except Exception as e:
                print(f"Failed to open file: {e}")

        self.next_image()

    def handle_background_click(self, x, y):
        self.pick_bg_color(x, y)

    def process_image(self, cx, cy):
        img = self.current_image
        target_w, target_h = TARGET_SIZE

        result = Image.new("RGB", (target_w, target_h), self.bg_color)
        canvas_cx = target_w // 2
        canvas_cy = target_h // 2
        offset_x = canvas_cx - cx
        offset_y = canvas_cy - cy

        from_x = max(0, -offset_x)
        from_y = max(0, -offset_y)
        to_x = min(img.width, target_w - offset_x)
        to_y = min(img.height, target_h - offset_y)

        cropped = img.crop((from_x, from_y, to_x, to_y))
        paste_x = max(offset_x, 0)
        paste_y = max(offset_y, 0)
        result.paste(cropped, (paste_x, paste_y))

        original_path = self.image_paths[self.current_index]
        rel_path = os.path.relpath(original_path, self.base_folder)
        rel_dir = os.path.dirname(rel_path)

        save_folder = os.path.join(self.output_folder, rel_dir)
        os.makedirs(save_folder, exist_ok=True)

        name, _ = os.path.splitext(os.path.basename(original_path))
        output_path = os.path.join(save_folder, f"{name}_resized.bmp")

        result.save(output_path, format="BMP")
        self.last_output_path = os.path.abspath(output_path)

    def on_mouse_move(self, event):
        if self.preview_mode_var.get() != "Show Crop Preview" or not self.current_image:
            return

        if self.preview_window and not self.preview_window.winfo_exists():
            self.preview_window = None
            return

        disp_w, disp_h = self.tk_image.width(), self.tk_image.height()
        orig_w, orig_h = self.current_image.size
        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h

        center_x = int(event.x * scale_x)
        center_y = int(event.y * scale_y)

        preview = self.simulate_process_image(center_x, center_y)

        if not self.preview_window:
            self.preview_window = tk.Toplevel(self.root)
            self.preview_window.title("Live Crop Preview")
            self.preview_window.protocol("WM_DELETE_WINDOW", self.destroy_preview_window)
            self.preview_label = tk.Label(self.preview_window, text="Live Crop Preview")
            self.preview_label.pack()
            self.preview_canvas = tk.Label(self.preview_window)
            self.preview_canvas.pack()

        preview = preview.resize((200, 200))
        self.preview_tk = ImageTk.PhotoImage(preview)
        self.preview_canvas.config(image=self.preview_tk)

    def simulate_process_image(self, cx, cy):
        img = self.current_image
        target_w, target_h = TARGET_SIZE

        result = Image.new("RGB", (target_w, target_h), self.bg_color)
        canvas_cx = target_w // 2
        canvas_cy = target_h // 2
        offset_x = canvas_cx - cx
        offset_y = canvas_cy - cy

        from_x = max(0, -offset_x)
        from_y = max(0, -offset_y)
        to_x = min(img.width, target_w - offset_x)
        to_y = min(img.height, target_h - offset_y)

        cropped = img.crop((from_x, from_y, to_x, to_y))
        paste_x = max(offset_x, 0)
        paste_y = max(offset_y, 0)
        result.paste(cropped, (paste_x, paste_y))

        return result

    def next_image(self, event=None):
        if self.current_index < len(self.image_paths) - 1:
            self.current_index += 1
            self.show_image()
        else:
            messagebox.showinfo("Done", "All images processed!")
            self.root.quit()

    def prev_image(self, event=None):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image()

    def toggle_bg_color_box(self, init=False):
        global SHOW_BG_COLOR_BOX

        if not init:
            SHOW_BG_COLOR_BOX = not SHOW_BG_COLOR_BOX
            self.bg_color_toggle_var.set(SHOW_BG_COLOR_BOX)

        self.adjust_frames()
        self.update_menu_states()

    def update_menu_states(self):
        if hasattr(self, 'bg_color_menu'):
            # Update the state of Toggle Hex Color and Change Location menu items
            self.bg_color_menu.entryconfig(1, state="normal" if SHOW_BG_COLOR_BOX else "disabled")  # Toggle Hex Color
            self.bg_color_menu.entryconfig(2, state="normal" if SHOW_BG_COLOR_BOX else "disabled")  # Change Location

    def adjust_frames(self):
        # Remove all widgets first
        self.bg_color_label.pack_forget()
        self.canvas.pack_forget()

        # Configure root window to handle layout properly
        self.root.update_idletasks()
        
        # Pack in correct order
        if self.bg_color_box_position == "top":
            if SHOW_BG_COLOR_BOX:
                self.bg_color_label.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
            self.canvas.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        else:  # bottom position
            self.canvas.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
            if SHOW_BG_COLOR_BOX:
                self.bg_color_label.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        # Force update of the layout
        self.root.update_idletasks()

    def destroy_preview_window(self):
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
        self.preview_mode_var.set("Off")
    
    def rgb_to_hex(self, rgb):
        return "#%02x%02x%02x" % rgb
    
    def bg_color_position_dialog(self):
        self.position_window = tk.Toplevel(self.root)
        self.position_window.title("BG Color Box Position")
        self.position_window.grab_set()
        self.position_window.focus_force()

        # Position the window to the right of the main window
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        
        self.position_window.update_idletasks()  # Update window size
        window_width = self.position_window.winfo_width()
        window_height = self.position_window.winfo_height()
        
        # Position to the right of the main window with some padding
        x = main_x + main_width + 10
        y = main_y
        self.position_window.geometry(f"+{x}+{y}")

        position_var = tk.StringVar(value=self.bg_color_box_position)
        
        def update_position():
            self.bg_color_box_position = position_var.get()
            self.adjust_frames()

        tk.Radiobutton(self.position_window, text="Top", variable=position_var, value="top", command=update_position).pack(anchor="w")
        tk.Radiobutton(self.position_window, text="Bottom", variable=position_var, value="bottom", command=update_position).pack(anchor="w")
        
        tk.Button(self.position_window, text="OK", command=self.position_window.destroy).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizerApp(root)
    root.mainloop()
