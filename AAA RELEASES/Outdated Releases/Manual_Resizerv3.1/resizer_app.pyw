import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import subprocess
from datetime import datetime
import webbrowser
from tkinter import ttk

from utils import rgb_to_hex, resource_path
from resolution_picker import ResolutionPicker
from config import TARGET_SIZE, OUTPUT_FOLDER, SHOW_BG_COLOR_BOX, BG_COLOR_BOX_POSITION
from stats_manager import StatsManager

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

        # Try setting icon with better error handling
        try:
            icon_path = os.path.abspath("mewsiepto.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                print(f"[Info] Successfully loaded icon from: {icon_path}")
            else:
                print(f"[Warning] Icon file not found at: {icon_path}")
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
        
        # Initialize resolution variables
        self.last_output_resolution_vars = []
        self.crop_preview_resolution_vars = []

        # Store menus as instance variables
        self.preview_mode_menu = None
        self.options_menu = None

        # Initialize stats manager
        self.stats_manager = StatsManager()

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
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit (Alt+F4)", command=self.quit_app, accelerator="Alt+F4")
        menubar.add_cascade(label="🗂️ File", menu=file_menu)

        self.root.bind('<Alt-F4>', lambda e: self.quit_app())

        self.options_menu = tk.Menu(menubar, tearoff=0)
        self.options_menu.add_command(label="🖱️ Mouse Mode", command=self.mouse_mode_dialog)

        # Create Preview Mode menu
        self.preview_mode_menu = tk.Menu(self.options_menu, tearoff=0)
        self.preview_mode_menu.add_radiobutton(label="🔲 Off", variable=self.preview_mode_var, value="Off")
        self.preview_mode_menu.add_radiobutton(label="🖼️ Show Last Output", variable=self.preview_mode_var, value="Show Last Output")
        self.preview_mode_menu.add_radiobutton(label="🔍 Show Crop Preview", variable=self.preview_mode_var, value="Show Crop Preview")
        
        # Add initial separator for resolution sections
        self.preview_mode_menu.add_separator()
        
        # Add Last Output Resolutions section
        self.preview_mode_menu.add_command(label="📏 Last Output Resolutions:", state="disabled")
        for i, (w, h) in enumerate(TARGET_SIZE):
            var1 = tk.BooleanVar(value=False)  # Ensure it starts unchecked
            self.last_output_resolution_vars.append(var1)
            self.preview_mode_menu.add_checkbutton(label=f"  {w}x{h}", variable=var1,
                                          command=lambda idx=i: self.update_last_output_preview(idx))
        
        self.preview_mode_menu.add_separator()
        
        # Add Crop Preview Resolutions section
        self.preview_mode_menu.add_command(label="📏 Crop Preview Resolutions:", state="disabled")
        for i, (w, h) in enumerate(TARGET_SIZE):
            var2 = tk.BooleanVar(value=False)  # Ensure it starts unchecked
            self.crop_preview_resolution_vars.append(var2)
            self.preview_mode_menu.add_checkbutton(label=f"  {w}x{h}", variable=var2,
                                           command=lambda idx=i: self.update_preview_windows())
        
        self.options_menu.add_cascade(label="🎞️ Preview Mode", menu=self.preview_mode_menu)

        self.bg_color_menu = tk.Menu(self.options_menu, tearoff=0)
        self.bg_color_menu.add_checkbutton(label="🖌️ Toggle BG Color Box", variable=self.bg_color_toggle_var, command=self.toggle_bg_color_box)
        self.bg_color_menu.add_command(label="🎨 Toggle Hex Color", command=self.toggle_hex_label)
        self.bg_color_menu.add_command(label="📏 Change Location", command=self.bg_color_position_dialog)
        self.options_menu.add_cascade(label="🎨 BG Color Box Options", menu=self.bg_color_menu)

        menubar.add_cascade(label="⚙️ Options", menu=self.options_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="📚 Manual", command=self.show_manual)
        help_menu.add_command(label="📊 Statistics", command=self.show_statistics)
        help_menu.add_command(label="❓ About", command=self.open_about_window)
        menubar.add_cascade(label="❓ Help", menu=help_menu)

        self.root.config(menu=menubar)
        self.update_menu_states()

    def toggle_hex_label(self):
        self.show_hex_in_label = not self.show_hex_in_label
        self.update_bg_color_label()

    def update_bg_color_label(self):
        if self.show_hex_in_label:
            text = rgb_to_hex(self.bg_color)
        else:
            text = "BG Color"
        
        # Get contrasting text color
        text_color = self.get_contrasting_text_color(self.bg_color)
        
        self.bg_color_label.config(
            text=text,
            bg=rgb_to_hex(self.bg_color),
            fg=text_color
        )

    def open_about_window(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("400x200")
        about_window.resizable(False, False)

        tk.Label(about_window, text="Manual Center Image Resizer", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(about_window, text="Created for easy manual center-based image cropping and resizing.", wraplength=380, justify="center").pack(pady=5)

        link = tk.Label(about_window, text="GitHub Repository", fg="blue", cursor="hand2")
        link.pack(pady=10)
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/mewsieworld/FuseBatchResizeTool"))

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
            # Update the preview mode menu with new resolutions
            self.update_preview_mode_menu()
            
            # Ensure window is wide enough after setting resolution
            self.root.update_idletasks()
            current_width = self.root.winfo_width()
            if current_width < 400:
                self.root.geometry(f"400x{self.root.winfo_height()}")
            
            # If we're in the middle of processing images, show a message
            if self.current_image is not None:
                messagebox.showinfo("Resolution Updated", 
                    f"Selected {len(TARGET_SIZE)} resolution(s):\n" + 
                    "\n".join(f"{w}x{h}" for w, h in TARGET_SIZE))
        else:
            if self.current_image is None:  # Only quit if this is the initial launch
                self.root.quit()

    def load_images(self):
        self.base_folder = filedialog.askdirectory(title="Select Folder of Images")
        if not self.base_folder:
            self.root.quit()

        # First check if there are any images in the selected folder
        self.image_paths = []
        for root_dir, _, files in os.walk(self.base_folder):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    self.image_paths.append(os.path.join(root_dir, file))

        if not self.image_paths:
            messagebox.showerror("Error", "No images found. Please select a folder containing images.")
            self.load_images()  # Prompt for folder selection again
            return

        # Only ask about timestamp folder if images were found
        use_timestamp = messagebox.askyesno("New Output Subfolder", "Do you want to create a timestamped output folder inside 'output_resized'?")

        # Create base output folder
        base_output = os.path.join(os.path.dirname(__file__), "output_resized")
        os.makedirs(base_output, exist_ok=True)

        if use_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_folder = os.path.join(base_output, timestamp)
        else:
            self.output_folder = base_output

        # Don't create the output folder yet - it will be created as needed
        # to prevent empty folders from being created

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

        # Get the current canvas size
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # Calculate center position
        self.image_x = canvas_w // 2
        self.image_y = canvas_h // 2

        # Create image at center position
        self.canvas.create_image(self.image_x, self.image_y, anchor=tk.CENTER, image=self.tk_image)

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
            # Calculate the top-left position of the displayed image
            img_left = self.image_x - (self.tk_image.width() // 2)
            img_top = self.image_y - (self.tk_image.height() // 2)
            
            # Get the scale factors
            scale_x = self.current_image.width / self.tk_image.width()
            scale_y = self.current_image.height / self.tk_image.height()
            
            # Convert click coordinates to original image coordinates
            img_x = int((x - img_left) * scale_x)
            img_y = int((y - img_top) * scale_y)

            # Check if the coordinates are within the image bounds
            if (0 <= img_x < self.current_image.width and 
                0 <= img_y < self.current_image.height):
                self.bg_color = self.current_image.getpixel((img_x, img_y))
                self.bg_color_label.config(bg=rgb_to_hex(self.bg_color))
                self.update_bg_color_label()
        elif self.right_click_mode == "center":
            self.handle_center_click(x, y)

    def pick_bg_color(self, x, y):
        if not self.tk_image:
            return
            
        # Calculate the top-left position of the displayed image
        img_left = self.image_x - (self.tk_image.width() // 2)
        img_top = self.image_y - (self.tk_image.height() // 2)
        
        # Get the scale factors
        scale_x = self.current_image.width / self.tk_image.width()
        scale_y = self.current_image.height / self.tk_image.height()
        
        # Convert click coordinates to original image coordinates
        img_x = int((x - img_left) * scale_x)
        img_y = int((y - img_top) * scale_y)
        
        if (0 <= img_x < self.current_image.width and 
            0 <= img_y < self.current_image.height):
            self.bg_color = self.current_image.getpixel((img_x, img_y))
            self.update_bg_color_label()
        self.eyedropper_active = False
        self.root.title("Manual Center Image Resizer")

    def handle_center_click(self, x, y):
        if not self.current_image:
            return
            
        # Get the scale factors and image dimensions
        scale_x = self.current_image.width / self.tk_image.width()
        scale_y = self.current_image.height / self.tk_image.height()
        
        # Calculate the top-left position of the displayed image
        img_left = self.image_x - (self.tk_image.width() // 2)
        img_top = self.image_y - (self.tk_image.height() // 2)
        
        # Convert click coordinates to original image coordinates
        img_x = int((x - img_left) * scale_x)
        img_y = int((y - img_top) * scale_y)
        
        # Process the image
        self.process_image(img_x, img_y)

        # Update preview if enabled
        if self.preview_mode_var.get() == "Show Last Output" and self.last_output_path:
            try:
                # Create or update the last output preview window
                if not hasattr(self, 'last_output_window') or not self.last_output_window.winfo_exists():
                    self.last_output_window = tk.Toplevel(self.root)
                    self.last_output_window.title("Last Output Preview")
                    self.last_output_window.protocol("WM_DELETE_WINDOW", lambda: self.last_output_window.destroy())
                    
                    # Create a frame for the preview label and settings
                    top_frame = tk.Frame(self.last_output_window)
                    top_frame.pack(fill=tk.X, padx=5, pady=5)
                    
                    tk.Label(top_frame, text="Last Output Preview").pack(side=tk.LEFT)
                    
                    # Add resolution selection frame
                    resolution_frame = tk.Frame(top_frame)
                    resolution_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
                    
                    tk.Label(resolution_frame, text="Show:").pack(side=tk.LEFT)
                    
                    # Create a variable to track selected resolutions for last output
                    self.last_output_resolution_vars = []
                    for i, (w, h) in enumerate(TARGET_SIZE):
                        var = tk.BooleanVar(value=False)  # Ensure it starts unchecked
                        self.last_output_resolution_vars.append(var)
                        cb = tk.Checkbutton(resolution_frame, text=f"{w}x{h}", variable=var,
                                          command=lambda idx=i: self.update_last_output_preview(idx))
                        cb.pack(side=tk.LEFT, padx=2)
                    
                    # Create a scrollable canvas for previews
                    self.last_output_canvas = tk.Frame(self.last_output_window)
                    self.last_output_canvas.pack(fill=tk.BOTH, expand=True)
                
                # Update the preview
                self.update_last_output_preview()
                
            except Exception as e:
                print(f"Failed to open file: {e}")

        # Move to next image
        if self.current_index < len(self.image_paths) - 1:
            self.current_index += 1
            self.show_image()
        else:
            messagebox.showinfo("Done", "All images processed! Click 'Open Folder' to process more images or 'Exit' to quit.")
            # Reset to first image
            self.current_index = 0
            self.show_image()

    def handle_background_click(self, x, y):
        # Calculate the top-left position of the displayed image
        img_left = self.image_x - (self.tk_image.width() // 2)
        img_top = self.image_y - (self.tk_image.height() // 2)
        
        # Get the scale factors
        scale_x = self.current_image.width / self.tk_image.width()
        scale_y = self.current_image.height / self.tk_image.height()
        
        # Convert click coordinates to original image coordinates
        img_x = int((x - img_left) * scale_x)
        img_y = int((y - img_top) * scale_y)
        
        if (0 <= img_x < self.current_image.width and 
            0 <= img_y < self.current_image.height):
            self.bg_color = self.current_image.getpixel((img_x, img_y))
            self.update_bg_color_label()

    def process_image(self, cx, cy):
        img = self.current_image
        target_sizes = TARGET_SIZE if isinstance(TARGET_SIZE, list) else [TARGET_SIZE]
        
        # Get the relative path structure from the input folder
        original_path = self.image_paths[self.current_index]
        rel_path = os.path.relpath(original_path, self.base_folder)
        rel_dir = os.path.dirname(rel_path)
        filename = os.path.basename(rel_path)
        name = os.path.splitext(filename)[0]

        # Process for each target size
        for target_w, target_h in target_sizes:
            # Create the resized image
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

            # Construct output path
            if len(target_sizes) > 1:
                # Multiple resolutions: output_resized/[timestamp]/WxH/original/folder/structure
                resolution_folder = f"{target_w}x{target_h}"
                if rel_dir:
                    save_path = os.path.join(self.output_folder, resolution_folder, rel_dir)
                else:
                    save_path = os.path.join(self.output_folder, resolution_folder)
            else:
                # Single resolution: output_resized/[timestamp]/original/folder/structure
                save_path = os.path.join(self.output_folder, rel_dir) if rel_dir else self.output_folder

            # Create output directory if it doesn't exist
            os.makedirs(save_path, exist_ok=True)

            # Save the image
            output_path = os.path.join(save_path, f"{name}_resized.bmp")
            result.save(output_path, format="BMP")
            self.last_output_path = os.path.abspath(output_path)

        # Update statistics
        self.stats_manager.add_processed_file(filename, TARGET_SIZE, self.bg_color)

    def on_mouse_move(self, event):
        if self.preview_mode_var.get() != "Show Crop Preview" or not self.current_image:
            return

        x, y = self.correct_coordinates(event)
        if self.eyedropper_active:
            return

        # Create control window if it doesn't exist
        if not hasattr(self, 'preview_control_window') or not self.preview_control_window.winfo_exists():
            self.preview_control_window = tk.Toplevel(self.root)
            self.preview_control_window.title("Live Crop Preview Controls")
            self.preview_control_window.protocol("WM_DELETE_WINDOW", self.destroy_preview_window)
            
            # Create a frame for the controls
            control_frame = tk.Frame(self.preview_control_window)
            control_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(control_frame, text="Show Resolutions:").pack(side=tk.LEFT)
            
            # Create checkboxes for each resolution
            self.crop_preview_resolution_vars = []
            for i, (w, h) in enumerate(TARGET_SIZE):
                var = tk.BooleanVar(value=False)  # Ensure it starts unchecked
                self.crop_preview_resolution_vars.append(var)
                cb = tk.Checkbutton(control_frame, text=f"{w}x{h}", variable=var,
                                  command=lambda idx=i: self.update_preview_windows())
                cb.pack(side=tk.LEFT, padx=2)

        # Initialize preview windows dictionary if it doesn't exist
        if not hasattr(self, 'preview_windows'):
            self.preview_windows = {}

        # Update all preview windows
        self.update_preview_windows(x, y)

    def update_preview_windows(self, center_x=None, center_y=None):
        if not hasattr(self, 'preview_windows'):
            return

        # Get selected resolutions
        selected_resolutions = []
        for i, var in enumerate(self.crop_preview_resolution_vars):
            if var.get():
                selected_resolutions.append((i, TARGET_SIZE[i]))

        # Close windows for unselected resolutions
        current_indices = [i for i, _ in selected_resolutions]
        for idx in list(self.preview_windows.keys()):
            if idx not in current_indices:
                if self.preview_windows[idx].winfo_exists():
                    self.preview_windows[idx].destroy()
                del self.preview_windows[idx]

        if not center_x or not center_y:
            return

        # Update or create windows for selected resolutions
        for idx, (w, h) in selected_resolutions:
            if idx not in self.preview_windows or not self.preview_windows[idx].winfo_exists():
                # Create new window
                preview_window = tk.Toplevel(self.root)
                preview_window.title(f"Live Preview {w}x{h}")
                preview_window.protocol("WM_DELETE_WINDOW", 
                    lambda i=idx: self.close_preview_window(i))
                
                # Allow window to be resized
                preview_window.resizable(True, True)
                
                # Create main frame with padding for title
                main_frame = ttk.Frame(preview_window, padding="10 30 10 10")
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # Create a frame that will center the preview
                center_frame = ttk.Frame(main_frame)
                center_frame.pack(fill=tk.BOTH, expand=True)
                
                # Configure grid weights to center the preview
                center_frame.grid_rowconfigure(0, weight=1)
                center_frame.grid_columnconfigure(0, weight=1)
                
                # Create preview frame with exact dimensions
                preview_frame = ttk.Frame(center_frame, width=w, height=h)
                preview_frame.grid(row=0, column=0)
                preview_frame.grid_propagate(False)  # Maintain exact size
                
                # Create preview label
                preview_label = ttk.Label(preview_frame)
                preview_label.place(relx=0.5, rely=0.5, anchor="center")  # Center in frame
                
                self.preview_windows[idx] = preview_window
                self.preview_windows[idx].preview_label = preview_label
                
                # Set initial window size to exact resolution plus padding
                window_width = w + 40  # Add padding for window borders
                window_height = h + 80  # Add space for title bar, borders, and padding
                
                # Set initial window size
                preview_window.geometry(f"{window_width}x{window_height}")
                
                # Store original dimensions for reference
                preview_window.original_width = w
                preview_window.original_height = h
            
            # Update the preview image
            self.update_preview_image(idx, center_x, center_y)

    def close_preview_window(self, idx):
        if idx in self.preview_windows:
            self.preview_windows[idx].destroy()
            del self.preview_windows[idx]
            # Uncheck the corresponding checkbox
            self.crop_preview_resolution_vars[idx].set(False)

    def destroy_preview_window(self):
        if hasattr(self, 'preview_control_window') and self.preview_control_window.winfo_exists():
            self.preview_control_window.destroy()
        
        if hasattr(self, 'preview_windows'):
            for window in self.preview_windows.values():
                if window.winfo_exists():
                    window.destroy()
            self.preview_windows.clear()
            
        self.preview_mode_var.set("Off")

    def next_image(self, event=None):
        if self.current_index < len(self.image_paths) - 1:
            self.current_index += 1
            self.show_image()
        else:
            messagebox.showinfo("Done", "All images processed! Click 'Open Folder' to process more images or 'Exit' to quit.")
            # Reset to first image
            self.current_index = 0
            self.show_image()

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

    def update_last_output_preview(self, index=None):
        if not hasattr(self, 'last_output_window') or not self.last_output_window.winfo_exists():
            return
            
        try:
            # Get the selected resolutions
            selected_resolutions = []
            for i, var in enumerate(self.last_output_resolution_vars):
                if var.get():
                    selected_resolutions.append(TARGET_SIZE[i])
            
            if not selected_resolutions:
                return

            # Clear existing preview widgets
            for widget in self.last_output_canvas.winfo_children():
                widget.destroy()

            # Create a frame for vertical layout with scrolling
            preview_frame = ttk.Frame(self.last_output_canvas)
            preview_frame.pack(fill=tk.BOTH, expand=True)
            
            # Add each resolution and its preview
            for w, h in selected_resolutions:
                # Create a container frame for this resolution
                res_frame = ttk.Frame(preview_frame)
                res_frame.pack(pady=10)
                
                # Add resolution label
                resolution_label = ttk.Label(res_frame, text=f"{w}x{h}", font=("Arial", 10, "bold"))
                resolution_label.pack(pady=(0, 5))

                # Create a frame to hold the image at exact size
                img_frame = ttk.Frame(res_frame, width=w, height=h)
                img_frame.pack()
                img_frame.pack_propagate(False)  # Maintain exact size

                # Load the image at its actual resolution
                img = Image.open(self.last_output_path)
                
                # Convert to PhotoImage - no resizing
                photo = ImageTk.PhotoImage(img)
                
                # Create and pack the image label
                img_label = ttk.Label(img_frame, image=photo)
                img_label.image = photo  # Keep a reference to prevent garbage collection
                img_label.place(relx=0.5, rely=0.5, anchor="center")  # Center in frame
            
            # Update the window title with the number of previews
            self.last_output_window.title(f"Last Output Preview - {len(selected_resolutions)} resolution(s)")
            
        except Exception as e:
            print(f"Error updating last output preview: {e}")

    def update_preview_mode_menu(self):
        if not self.preview_mode_menu:
            return

        # Clear existing resolution entries while keeping the mode selections
        while self.preview_mode_menu.index('end') > 3:  # Keep the first three radio buttons and separator
            self.preview_mode_menu.delete(4)
        
        # Clear existing variables
        self.last_output_resolution_vars.clear()
        self.crop_preview_resolution_vars.clear()
        
        # Add Last Output Resolutions section
        self.preview_mode_menu.add_command(label="📏 Last Output Resolutions:", state="disabled")
        for i, (w, h) in enumerate(TARGET_SIZE):
            var1 = tk.BooleanVar(value=False)  # Ensure it starts unchecked
            self.last_output_resolution_vars.append(var1)
            self.preview_mode_menu.add_checkbutton(label=f"  {w}x{h}", variable=var1,
                                          command=lambda idx=i: self.update_last_output_preview(idx))
        
        self.preview_mode_menu.add_separator()
        
        # Add Crop Preview Resolutions section
        self.preview_mode_menu.add_command(label="📏 Crop Preview Resolutions:", state="disabled")
        for i, (w, h) in enumerate(TARGET_SIZE):
            var2 = tk.BooleanVar(value=False)  # Ensure it starts unchecked
            self.crop_preview_resolution_vars.append(var2)
            self.preview_mode_menu.add_checkbutton(label=f"  {w}x{h}", variable=var2,
                                           command=lambda idx=i: self.update_preview_windows())

    def update_preview_image(self, idx, center_x, center_y):
        if idx not in self.preview_windows or not self.preview_windows[idx].winfo_exists():
            return
            
        preview_window = self.preview_windows[idx]
        
        # Create preview at exact target dimensions
        preview = self.simulate_process_image(center_x, center_y, 
                                           preview_window.original_width, 
                                           preview_window.original_height)
        
        # Convert to PhotoImage at exact size - no resizing
        photo = ImageTk.PhotoImage(preview)
        
        # Update the label
        preview_window.preview_label.configure(image=photo)
        preview_window.preview_label.image = photo  # Keep reference

    def simulate_process_image(self, cx, cy, target_w, target_h):
        # Convert display coordinates to original image coordinates
        scale_x = self.current_image.width / self.tk_image.width()
        scale_y = self.current_image.height / self.tk_image.height()
        
        # Calculate the top-left position of the displayed image
        img_left = self.image_x - (self.tk_image.width() // 2)
        img_top = self.image_y - (self.tk_image.height() // 2)
        
        # Convert click coordinates to original image coordinates
        orig_x = int((cx - img_left) * scale_x)
        orig_y = int((cy - img_top) * scale_y)
        
        # Create new image at target size
        result = Image.new("RGB", (target_w, target_h), self.bg_color)
        
        # Calculate offsets to center the image around the clicked point
        offset_x = target_w // 2 - orig_x
        offset_y = target_h // 2 - orig_y
        
        # Calculate crop coordinates
        from_x = max(0, -offset_x)
        from_y = max(0, -offset_y)
        to_x = min(self.current_image.width, target_w - offset_x)
        to_y = min(self.current_image.height, target_h - offset_y)
        
        # Crop and paste
        cropped = self.current_image.crop((from_x, from_y, to_x, to_y))
        paste_x = max(offset_x, 0)
        paste_y = max(offset_y, 0)
        result.paste(cropped, (paste_x, paste_y))
        
        return result

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

    def show_statistics(self):
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Application Statistics")
        stats_window.geometry("600x800")
        stats_window.resizable(True, True)
        
        # Create main frame with padding
        main_frame = ttk.Frame(stats_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Get formatted stats
        stats = self.stats_manager.get_formatted_stats()
        
        # Create sections
        sections = [
            ("General Statistics", [
                ("Total Files Processed", str(stats["total_files"])),
                ("Total Time Spent", stats["total_time"]),
                ("Estimated Time Saved", stats["time_saved"]),
                ("Total Sessions", str(stats["session_count"])),
                ("Files This Session", str(stats["current_session_files"]))
            ]),
            ("Recent Activity", [
                ("Last Access", stats["last_access"]),
                ("Last File Processed", stats.get("last_file", {}).get("name", "None")),
                ("Last File Time", stats.get("last_file", {}).get("time", "None"))
            ])
        ]
        
        row = 0
        for section_title, items in sections:
            # Section title
            ttk.Label(main_frame, text=section_title, font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 5))
            row += 1
            
            # Section items
            for label, value in items:
                ttk.Label(main_frame, text=label + ":", font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=(20, 10))
                ttk.Label(main_frame, text=value, font=("Arial", 10)).grid(row=row, column=1, sticky="w")
                row += 1
        
        # Top Colors Section
        ttk.Label(main_frame, text="Top 5 Background Colors", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(20, 5))
        row += 1
        
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=20)
        
        for i, (color, count) in enumerate(stats["top_colors"]):
            color_box = tk.Label(color_frame, text=f"{color} ({count})", width=20, bg=color)
            if self.is_dark_color(color):
                color_box.config(fg="white")
            color_box.pack(pady=2)
        
        row += 1
        
        # Top Resolutions Section
        ttk.Label(main_frame, text="Top 5 Resolutions", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(20, 5))
        row += 1
        
        for resolution, count in stats["top_resolutions"]:
            text = f"{resolution} ({count} times)"
            ttk.Label(main_frame, text=text, font=("Arial", 10)).grid(row=row, column=0, columnspan=2, sticky="w", padx=20)
            row += 1

    def is_dark_color(self, hex_color):
        # Remove the '#' if present
        hex_color = hex_color.lstrip('#')
        
        # Convert hex to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Calculate perceived brightness
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        
        return brightness < 128

    def quit_app(self):
        self.stats_manager.end_session()
        self.root.quit()

    def show_manual(self):
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Manual")
        
        # Create main frame with padding
        main_frame = ttk.Frame(manual_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create paned window for split view
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Create left frame for topics with fixed width
        topics_frame = ttk.Frame(paned, width=200)  # Fixed width for topics
        topics_frame.pack(fill=tk.BOTH, expand=True)
        topics_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Create right frame for content
        content_frame = ttk.Frame(paned)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add frames to paned window with specific weights
        paned.add(topics_frame, weight=0)  # Fixed width for topics
        paned.add(content_frame, weight=1)  # Content expands
        
        # Create scrollable frames
        topics_canvas = tk.Canvas(topics_frame)
        topics_scrollbar = ttk.Scrollbar(topics_frame, orient="vertical", command=topics_canvas.yview)
        topics_scrollable_frame = ttk.Frame(topics_canvas)
        
        content_canvas = tk.Canvas(content_frame)
        content_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=content_canvas.yview)
        content_scrollable_frame = ttk.Frame(content_canvas)
        
        # Configure scrollable frames
        topics_scrollable_frame.bind(
            "<Configure>",
            lambda e: topics_canvas.configure(scrollregion=topics_canvas.bbox("all"))
        )
        content_scrollable_frame.bind(
            "<Configure>",
            lambda e: content_canvas.configure(scrollregion=content_canvas.bbox("all"))
        )
        
        # Create windows in canvases
        topics_canvas.create_window((0, 0), window=topics_scrollable_frame, anchor="nw")
        content_canvas.create_window((0, 0), window=content_scrollable_frame, anchor="nw")
        
        # Pack scrollbars and canvases
        topics_scrollbar.pack(side="right", fill="y")
        topics_canvas.pack(side="left", fill="both", expand=True)
        topics_canvas.configure(yscrollcommand=topics_scrollbar.set)
        
        content_scrollbar.pack(side="right", fill="y")
        content_canvas.pack(side="left", fill="both", expand=True)
        content_canvas.configure(yscrollcommand=content_scrollbar.set)
        
        # Load and parse markdown file
        try:
            with open("manual.md", "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split content into sections
            sections = []
            current_section = None
            current_content = []
            
            for line in content.split("\n"):
                if line.startswith("# "):
                    if current_section:
                        sections.append((current_section, "\n".join(current_content)))
                    current_section = line[2:].strip()
                    current_content = []
                elif line.startswith("## "):
                    if current_section:
                        sections.append((current_section, "\n".join(current_content)))
                    current_section = line[3:].strip()
                    current_content = []
                else:
                    current_content.append(line)
            
            if current_section:
                sections.append((current_section, "\n".join(current_content)))
            
            # Create topic buttons
            for i, (topic, _) in enumerate(sections):
                btn = ttk.Button(
                    topics_scrollable_frame,
                    text=topic,
                    command=lambda t=topic, c=sections[i][1]: self.update_manual_content(content_scrollable_frame, t, c)
                )
                btn.pack(fill="x", padx=5, pady=2)
            
            # Show first section by default
            if sections:
                self.update_manual_content(content_scrollable_frame, sections[0][0], sections[0][1])
                
                # Calculate required width
                manual_window.update_idletasks()  # Update to get actual sizes
                
                # Get screen dimensions
                screen_width = manual_window.winfo_screenwidth()
                screen_height = manual_window.winfo_screenheight()
                
                # Calculate optimal content width based on longest line
                longest_line = max(len(line) for section in sections for line in section[1].split('\n'))
                # Estimate pixels per character (approx 7 pixels per character for typical font)
                chars_to_pixels = 7
                content_width = min(longest_line * chars_to_pixels, int(screen_width * 0.6))
                
                # Total width includes:
                # - Fixed topics width (200px)
                # - Content width
                # - Scrollbars (40px)
                # - Padding and borders (60px)
                total_width = 200 + content_width + 100
                
                # Ensure window isn't too wide
                max_width = int(screen_width * 0.9)
                window_width = min(total_width, max_width)
                window_height = min(800, int(screen_height * 0.8))
                
                # Set window size and position
                manual_window.geometry(f"{window_width}x{window_height}")
                manual_window.minsize(window_width, 400)
                
                # Center the window
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
                manual_window.geometry(f"+{x}+{y}")
        
        except Exception as e:
            error_label = ttk.Label(content_scrollable_frame, text=f"Error loading manual: {str(e)}")
            error_label.pack(padx=10, pady=10)

    def update_manual_content(self, frame, topic, content):
        # Clear existing content
        for widget in frame.winfo_children():
            widget.destroy()
        
        # Add topic title
        title_label = ttk.Label(frame, text=topic, font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Create a frame for the content
        content_frame = ttk.Frame(frame)
        content_frame.pack(padx=10, pady=5, fill="x")
        
        # Process content line by line
        current_list = None
        current_list_items = []
        code_block = False
        code_content = []
        paragraph_lines = []
        
        def create_paragraph(lines):
            if lines:
                text = ' '.join(line.strip() for line in lines if line.strip())
                if text:
                    label = ttk.Label(
                        content_frame,
                        text=text,
                        wraplength=550,  # Increased wraplength
                        justify="left"
                    )
                    label.pack(fill="x", pady=3)
        
        for line in content.split('\n'):
            line = line.rstrip()
            
            # Handle code blocks
            if line.startswith("```"):
                # First flush any pending paragraph
                create_paragraph(paragraph_lines)
                paragraph_lines = []
                
                if not code_block:
                    code_block = True
                    code_content = []
                else:
                    code_block = False
                    # Create a frame for code block with monospace font
                    code_frame = ttk.Frame(content_frame, relief="solid", borderwidth=1)
                    code_frame.pack(fill="x", pady=5)
                    code_label = ttk.Label(
                        code_frame,
                        text='\n'.join(code_content),
                        font=("Courier", 10),
                        background="#f0f0f0",
                        wraplength=550,
                        justify="left"
                    )
                    code_label.pack(padx=5, pady=5, fill="x")
                continue
            
            if code_block:
                code_content.append(line)
                continue
            
            # Handle headings
            if line.startswith("# "):
                create_paragraph(paragraph_lines)
                paragraph_lines = []
                ttk.Label(
                    content_frame,
                    text=line[2:],
                    font=("Arial", 12, "bold"),
                    wraplength=550,
                    justify="left"
                ).pack(fill="x", pady=(10, 5))
                continue
            elif line.startswith("## "):
                create_paragraph(paragraph_lines)
                paragraph_lines = []
                ttk.Label(
                    content_frame,
                    text=line[3:],
                    font=("Arial", 11, "bold"),
                    wraplength=550,
                    justify="left"
                ).pack(fill="x", pady=(8, 3))
                continue
            elif line.startswith("### "):
                create_paragraph(paragraph_lines)
                paragraph_lines = []
                ttk.Label(
                    content_frame,
                    text=line[4:],
                    font=("Arial", 10, "bold"),
                    wraplength=550,
                    justify="left"
                ).pack(fill="x", pady=(5, 2))
                continue
            
            # Handle lists
            if line.startswith("- ") or line.startswith("* "):
                create_paragraph(paragraph_lines)
                paragraph_lines = []
                
                if current_list is None:
                    current_list = ttk.Frame(content_frame)
                    current_list.pack(fill="x", pady=2)
                
                item_frame = ttk.Frame(current_list)
                item_frame.pack(fill="x", pady=1)
                
                bullet = ttk.Label(item_frame, text="•", font=("Arial", 10))
                bullet.pack(side="left", padx=(0, 5))
                
                # Process the list item text for formatting
                item_text = line[2:]  # Remove the bullet
                self.process_formatted_text(item_frame, item_text, is_list_item=True)
                continue
            elif current_list is not None:
                current_list = None
            
            # Handle empty lines as paragraph breaks
            if not line.strip():
                create_paragraph(paragraph_lines)
                paragraph_lines = []
                continue
            
            # Collect lines for paragraph
            paragraph_lines.append(line)
        
        # Handle any remaining paragraph
        create_paragraph(paragraph_lines)

    def process_formatted_text(self, parent, text, is_list_item=False):
        # Handle bold and italic text
        parts = text.split("**")
        if len(parts) > 1:  # Has bold text
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    if part.strip():
                        self.process_italic_text(parent, part, is_list_item)
                else:  # Bold text
                    ttk.Label(
                        parent,
                        text=part,
                        font=("Arial", 10, "bold"),
                        wraplength=500 if not is_list_item else 450,
                        justify="left"
                    ).pack(side="left")
        else:
            self.process_italic_text(parent, text, is_list_item)

    def process_italic_text(self, parent, text, is_list_item=False):
        parts = text.split("*")
        if len(parts) > 1:  # Has italic text
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    if part.strip():
                        ttk.Label(
                            parent,
                            text=part,
                            wraplength=500 if not is_list_item else 450,
                            justify="left"
                        ).pack(side="left")
                else:  # Italic text
                    ttk.Label(
                        parent,
                        text=part,
                        font=("Arial", 10, "italic"),
                        wraplength=500 if not is_list_item else 450,
                        justify="left"
                    ).pack(side="left")
        else:
            if text.strip():
                ttk.Label(
                    parent,
                    text=text,
                    wraplength=500 if not is_list_item else 450,
                    justify="left"
                ).pack(side="left")

    def get_contrasting_text_color(self, bg_color):
        # Convert RGB to relative luminance (WCAG 2.0 formula)
        r, g, b = bg_color
        r = r / 255
        g = g / 255
        b = b / 255
        
        # Apply gamma correction
        r = r if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        
        # Calculate relative luminance
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        # Return white for dark backgrounds, black for light backgrounds
        return "white" if luminance < 0.5 else "black"

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizerApp(root)
    root.mainloop()
