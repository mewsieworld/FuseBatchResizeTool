import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# Config
TARGET_SIZE = (200, 200)
BASE_OUTPUT_FOLDER = "output_resized"

class ImageResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Manual Center Image Resizer")

        self.image_paths = []
        self.base_folder = ""
        self.output_base_folder = BASE_OUTPUT_FOLDER
        self.timestamp_folder = ""
        self.current_index = 0
        self.current_image = None
        self.tk_image = None
        self.display_image = None
        self.bg_color = (255, 255, 255)
        self.left_click_mode = "center"
        self.right_click_mode = "background"

        self.setup_menu()
        self.canvas = tk.Canvas(root, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        root.bind("<Right>", self.next_image)
        root.bind("<Left>", self.prev_image)

        self.ask_resolution()

    def setup_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="📁 Open Folder...", command=self.select_folder)
        file_menu.add_command(label="🖼️ Set Resolution", command=self.ask_resolution)
        menubar.add_cascade(label="🗒️ File", menu=file_menu)

        mouse_menu = tk.Menu(menubar, tearoff=0)
        mouse_menu.add_command(label="🖱️ Mouse Mode", command=self.mouse_mode_dialog)
        menubar.add_cascade(label="🖱️ Mouse Mode", menu=mouse_menu)

        self.root.config(menu=menubar)


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
        return f"Left: {self.left_click_mode.capitalize()}  |  Right: {self.right_click_mode.capitalize()}"

    def switch_mouse_mode(self):
        if self.left_click_mode == "center":
            self.left_click_mode = "background"
            self.right_click_mode = "center"
        else:
            self.left_click_mode = "center"
            self.right_click_mode = "background"
        self.mode_label.config(text=self.get_mouse_mode_text())

    def ask_resolution(self):
        self.resolution_window = tk.Toplevel(self.root)
        self.resolution_window.title("Select Target Resolution")
        self.resolution_window.transient(self.root)
        self.resolution_window.grab_set()
        self.resolution_window.focus_force()
        self.resolution_window.lift()

    # Center the window
        self.resolution_window.update_idletasks()
        w = self.resolution_window.winfo_width()
        h = self.resolution_window.winfo_height()
        ws = self.resolution_window.winfo_screenwidth()
        hs = self.resolution_window.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.resolution_window.geometry(f'+{x}+{y}')

    # Set to 200x200 by default
        self.selected_option = tk.StringVar(value="200x200")

        options = [
            ("200x200", "200x200"),
            ("150x150", "150x150"),
            ("100x100", "100x100"),
            ("50x50", "50x50"),
            ("Custom", "custom")
        ]

        for text, value in options:
            rb = tk.Radiobutton(self.resolution_window, text=text, variable=self.selected_option, value=value, command=self.toggle_custom_entry)
            rb.pack(anchor=tk.W)

        self.custom_frame = tk.Frame(self.resolution_window)
        tk.Label(self.custom_frame, text="Width:").pack(side=tk.LEFT)
        self.custom_width = tk.Entry(self.custom_frame, width=5)
        self.custom_width.pack(side=tk.LEFT)
        tk.Label(self.custom_frame, text="Height:").pack(side=tk.LEFT)
        self.custom_height = tk.Entry(self.custom_frame, width=5)
        self.custom_height.pack(side=tk.LEFT)
        self.custom_frame.pack(anchor=tk.W)
        self.custom_frame.pack_forget()

        tk.Button(self.resolution_window, text="OK", command=self.confirm_resolution).pack(pady=5)

    def toggle_custom_entry(self):
        if self.selected_option.get() == "custom":
            self.custom_frame.pack(anchor=tk.W)
        else:
            self.custom_frame.pack_forget()

    def confirm_resolution(self):
        global TARGET_SIZE

        selection = self.selected_option.get()
        if not selection:
            messagebox.showerror("Error", "Please select a resolution.")
            return

        if selection == "custom":
            try:
                w = int(self.custom_width.get())
                h = int(self.custom_height.get())
                if w <= 0 or h <= 0:
                    raise ValueError
                TARGET_SIZE = (w, h)
            except ValueError:
                messagebox.showerror("Error", "Invalid custom dimensions.")
                return
        else:
            w, h = map(int, selection.split("x"))
            TARGET_SIZE = (w, h)

        self.resolution_window.destroy()

    def select_folder(self):
        self.base_folder = filedialog.askdirectory(title="Select Folder of Images")
        if not self.base_folder:
            return

        if messagebox.askyesno("New Output Subfolder", "Do you want to create a new timestamped subfolder for output?"):
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            self.timestamp_folder = os.path.join(BASE_OUTPUT_FOLDER, timestamp)
        else:
            self.timestamp_folder = BASE_OUTPUT_FOLDER

        os.makedirs(self.timestamp_folder, exist_ok=True)
        self.load_images()

    def load_images(self):
        self.image_paths = []

        for root_dir, _, files in os.walk(self.base_folder):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    self.image_paths.append(os.path.join(root_dir, file))

        if not self.image_paths:
            messagebox.showerror("Error", "No images found. Please select another folder.")
            self.select_folder()
            return

        self.current_index = 0
        self.show_image()

    def show_image(self):
        if not self.image_paths:
            return
        img_path = self.image_paths[self.current_index]
        self.current_image = Image.open(img_path).convert("RGB")

        self.display_image = self.current_image.copy()
        max_display_size = (600, 600)

        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.ANTIALIAS

        self.display_image.thumbnail(max_display_size, resample_filter)

        self.tk_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.delete("all")
        self.canvas.config(width=self.tk_image.width(), height=self.tk_image.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    def on_left_click(self, event):
        if self.left_click_mode == "center":
            self.center_click(event)
        else:
            self.background_click(event)

    def on_right_click(self, event):
        if self.right_click_mode == "background":
            self.background_click(event)
        else:
            self.center_click(event)

    def center_click(self, event):
        if not self.current_image or not self.display_image:
            return

        disp_w, disp_h = self.display_image.size
        orig_w, orig_h = self.current_image.size

        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h

        center_x = int(event.x * scale_x)
        center_y = int(event.y * scale_y)

        self.process_image(center_x, center_y)
        self.next_image()

    def background_click(self, event):
        if not self.current_image or not self.display_image:
            return

        disp_w, disp_h = self.display_image.size
        orig_w, orig_h = self.current_image.size

        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h

        sample_x = int(event.x * scale_x)
        sample_y = int(event.y * scale_y)

        sample_x = max(0, min(sample_x, orig_w - 1))
        sample_y = max(0, min(sample_y, orig_h - 1))

        self.bg_color = self.current_image.getpixel((sample_x, sample_y))
        print(f"Sampled background color: {self.bg_color}")

    def process_image(self, cx, cy):
        img = self.current_image
        orig_w, orig_h = img.size
        target_w, target_h = TARGET_SIZE

        canvas_cx = target_w // 2
        canvas_cy = target_h // 2

        offset_x = canvas_cx - cx
        offset_y = canvas_cy - cy

        result = Image.new("RGB", (target_w, target_h), self.bg_color)

        paste_x = offset_x
        paste_y = offset_y

        from_x = max(0, -paste_x)
        from_y = max(0, -paste_y)
        to_x = min(orig_w, target_w - paste_x)
        to_y = min(orig_h, target_h - paste_y)

        cropped = img.crop((from_x, from_y, to_x, to_y))
        final_paste_x = max(paste_x, 0)
        final_paste_y = max(paste_y, 0)

        result.paste(cropped, (final_paste_x, final_paste_y))

        original_path = self.image_paths[self.current_index]
        relative_path = os.path.relpath(original_path, self.base_folder)
        output_dir = os.path.join(self.timestamp_folder, os.path.dirname(relative_path))
        os.makedirs(output_dir, exist_ok=True)

        name, _ = os.path.splitext(os.path.basename(original_path))
        output_path = os.path.join(output_dir, f"{name}_resized.bmp")
        result.save(output_path, format="BMP")

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

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizerApp(root)
    root.mainloop()
