import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from tkinter import font # <<< ADDED FONT IMPORT >>>
from PIL import Image, ImageTk
import subprocess
from datetime import datetime
import webbrowser # <<< ENSURE webbrowser IS IMPORTED >>>
import re # <<< ENSURE re IS IMPORTED >>>
from tkinter import ttk
import traceback
import logging
from io import StringIO
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
    def __init__(self, root, manual_contents=None): # <<< MODIFIED to accept manual_contents >>>
        """Initialize the application."""
        try:
            # Basic window and state variables
            self.root = root
            self.root.title("Image Resizer")
            self.root.geometry("800x600")
            self.setup_successful = True # Initialize flag
            self.manual_content_data = manual_contents # <<< ADDED: Store manual content >>>
            
            # Image-related variables
            self.image_paths = []
            self.current_index = 0
            self.current_image = None
            self.display_image = None
            self.tk_image = None
            self.zoom_level = 1.0
            self.scroll_x = 0
            self.scroll_y = 0
            self.bg_color = (255, 0, 255, 255)  # Magenta (now RGBA)
            self.last_output_path = None
            
            # Mouse and interaction flags
            self.eyedropper_active = False
            self.is_panning = False
            self.last_mouse_x = 0
            self.last_mouse_y = 0
            # --- Use direct mode variables --- 
            self.left_click_mode = "center"  # Default
            self.right_click_mode = "background" # Default
            # self.mouse_mode_var = tk.StringVar(value="background") # Removed this
            
            # Track cursor position for crosshair
            self.cursor_x = 0
            self.cursor_y = 0
            
            # Grid and crosshair variables
            self.grid_lines = []
            self.last_crosshair_ids = []
            self.grid_size = 1  # Changed from 10 to 1 for 1x1 pixel grid
            
            # New crosshair variables
            self.crosshair_type = tk.StringVar(value="pixel")  # 'pixel' or 'cross'
            self.crosshair_size = tk.IntVar(value=1) # <<< ADDED CROSSHAIR SIZE VARIABLE >>>
            self.crosshair_color = "#FF0000"  # Red
            self.crosshair_use_negative = tk.BooleanVar(value=False)
            self.crosshair_patterns = {
            "pixel": [(0, 0)],  # Single pixel
                "cross": [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]  # Plus shape
            }
            
            # Display and layout variables
            self.base_width = 800
            self.base_height = 600
            self.zoom_factor = 1.1
            self.min_zoom = 0.1
            self.max_zoom = 10.0
            self.image_x = 0
            self.image_y = 0
            # Initialize position from config
            self.bg_color_box_position = "top"  # Default
            try:
                # First try to load from user_settings.ini (takes precedence)
                if os.path.exists("user_settings.ini"):
                    with open("user_settings.ini", "r") as f:
                        for line in f:
                            if line.startswith("BG_COLOR_BOX_POSITION"):
                                parts = line.split("=", 1)
                                if len(parts) == 2:
                                    pos = parts[1].strip().lower()
                                    if pos in ["top", "bottom"]:
                                        self.bg_color_box_position = pos
                                        print(f"DEBUG: Loaded position from user settings: {pos}")
                
                # Fall back to config module if no user settings
                elif 'BG_COLOR_BOX_POSITION' in globals() and BG_COLOR_BOX_POSITION is not None:
                    config_position = str(BG_COLOR_BOX_POSITION).lower()
                    if config_position in ["top", "bottom"]:
                        self.bg_color_box_position = config_position
                        print(f"DEBUG: Loaded bg_color_box_position from config module: {self.bg_color_box_position}")
                    else:
                        print(f"DEBUG: Invalid position in config: {config_position}, using default 'top'")
                else:
                    print("DEBUG: No BG_COLOR_BOX_POSITION found, using default 'top'")
            except Exception as e:
                print(f"DEBUG: Error loading position: {e}")
                self.bg_color_box_position = "top"  # Fallback to default
            
            print(f"DEBUG: Using bg_color_box_position: {self.bg_color_box_position}, type={type(self.bg_color_box_position)}")
            self.show_hex_in_label = False
            
            # Preview-related variables
            self.preview_windows = {}
            self.last_output_window = None
            self.preview_control_window = None
            self.preview_mode_menu = None
            self.crop_preview_resolution_vars = []
            self.last_output_resolution_vars = []
            
            # File and folder paths
            self.output_folder = OUTPUT_FOLDER
            self.base_folder = None
            
            # UI elements
            self.log_window = None
            self.log_text = None
            self.log_buffer = None
            self.logger = None
            self.debug_menu = None
            self.file_menu = None
            self.options_menu = None
            self.preview_menu = None
            self.mouse_menu = None
            self.bg_color_menu = None
            self.bg_color_label = None
            self.bg_color_reset = None
            self.color_frame = None
            self.canvas = None
            self.crosshair_menu = tk.Menu(self.root, tearoff=0)  # Initialize to prevent NoneType error
            self.position_window = None
            self.mouse_window = None
            self.mode_label = None
            self.crop_settings_dialog = None # <<< RE-ADD >>>
            self.last_output_settings_dialog = None # <<< RE-ADD >>>
        
            # Tkinter variables
            # --- Removed self.mouse_mode_var initialization --- 
            self.preview_mode_var = tk.StringVar(value="Off")
            self.show_grid_var = tk.BooleanVar(value=False)
            self.show_crosshair_var = tk.BooleanVar(value=False)
            self.grid_color_mode = tk.StringVar(value="custom")
            self.bg_color_toggle_var = tk.BooleanVar(value=SHOW_BG_COLOR_BOX)
            self.grid_color_var = tk.StringVar(value="black")
            # These will be populated by the dialogs or when dialogs are created
            self.crop_preview_dialog_vars = [] # <<< For crop settings dialog checkboxes >>>
            self.last_output_dialog_vars = [] # <<< For last output settings dialog checkboxes >>>
            self.grid_negative_checkbox_var = tk.BooleanVar(value=False) 
            
            # <<< ADDED: Store grid custom color explicitly >>>
            self.grid_custom_color = "black" 
            # <<< ADDED: Predefined grid colors >>>
            self.grid_colors = {
                "Black": "#000000", "White": "#FFFFFF", "Red": "#FF0000", "Green": "#00FF00",
                "Blue": "#0000FF", "Yellow": "#FFFF00", "Cyan": "#00FFFF", "Magenta": "#FF00FF"
            }
            # <<< END ADDED >>>


        
            # Initialize stats manager
            print("DEBUG INIT: Before StatsManager initialization") # ADDED
            self.stats_manager = StatsManager()
            print("DEBUG INIT: After StatsManager initialization") # ADDED
        
            # Set up logging
            print("DEBUG INIT: Before setup_logging") # ADDED
            self.setup_logging()
            print("DEBUG INIT: After setup_logging") # ADDED
            self.logger.info("Application initialized") # This now comes after setup_logging
            
            # Create the menu
            print("DEBUG INIT: Before create_menu") # ADDED
            self.create_menu()
            print("DEBUG INIT: After create_menu") # ADDED
            
            # Create the canvas
            self.canvas = tk.Canvas(self.root, bg="gray")
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            # Initialize color frame and label references (but don't create them yet)
            self.color_frame = None
            self.bg_color_label = None
            self.bg_color_reset = None
            self.bg_color_picker = None
            
            # Create background color menu
            self.bg_color_menu = tk.Menu(self.root, tearoff=0)
            self.bg_color_menu.add_command(label="Toggle Hex Display", command=self.toggle_hex_label)
            self.bg_color_menu.add_command(label="Reset to White", command=self.reset_background_color)
            self.bg_color_menu.add_command(label="Reset to Magenta", command=self.reset_bg_color)
            self.bg_color_menu.add_command(label="Pick Color...", command=self.pick_bg_color_dialog)
            
            # Bind mouse events (using handle_mouse_click for both)
            self.canvas.bind("<Button-1>", self.handle_mouse_click)
            self.canvas.bind("<Button-3>", self.handle_mouse_click)
            self.canvas.bind("<Motion>", self.on_mouse_move)
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            self.canvas.bind("<Button-4>", lambda e: self.on_mouse_wheel(e, delta=120))
            self.canvas.bind("<Button-5>", lambda e: self.on_mouse_wheel(e, delta=-120))
            self.canvas.bind("<B2-Motion>", self.on_mouse_wheel_hold)
            self.canvas.bind("<Button-2>", self.start_pan)
            self.canvas.bind("<ButtonRelease-2>", self.stop_pan)
            self.canvas.bind("<Control-MouseWheel>", self.on_horizontal_scroll)
            self.canvas.bind("<Control-Button-4>", lambda e: self.on_horizontal_scroll(e, delta=120))
            self.canvas.bind("<Control-Button-5>", lambda e: self.on_horizontal_scroll(e, delta=-120))
            self.canvas.bind("<Control-Shift-MouseWheel>", self.on_vertical_scroll)
            self.canvas.bind("<Control-Shift-Button-4>", lambda e: self.on_vertical_scroll(e, delta=120))
            self.canvas.bind("<Control-Shift-Button-5>", lambda e: self.on_vertical_scroll(e, delta=-120))
            
            # Bind keyboard shortcuts
            self.root.bind("<Left>", lambda e: self.prev_image())
            self.root.bind("<Right>", lambda e: self.next_image())
            self.root.bind("<Control-o>", lambda e: self.prompt_open_file_or_folder())
            self.root.bind("<Control-O>", lambda e: self.prompt_open_file_or_folder())
            self.root.bind("<Control-s>", lambda e: self.save_image())
            self.root.bind("<Control-S>", lambda e: self.save_all_images())
            self.root.bind("<Control-g>", self.handle_ctrl_g_grid_toggle)
            self.root.bind("<Control-d>", lambda e: self.toggle_log_window())
            self.root.bind("<Control-m>", lambda e: self.switch_mouse_mode())
            self.root.bind("<Control-r>", lambda e: self.reset_bg_color())
            self.root.bind("<Escape>", lambda e: self.cancel_eyedropper())
            self.root.bind("<Control-0>", self.reset_zoom)
            self.root.bind("<Control-plus>", self.zoom_in)
            self.root.bind("<Control-equal>", self.zoom_in)
            self.root.bind("<Control-minus>", self.zoom_out)
            
            # Adjust frames
            self.adjust_frames()
            
            # Force update of the display
            self.root.update_idletasks()
            
            # First prompt user for target size
            # self.ask_target_size() # Old call
            print("DEBUG INIT: Before ask_target_size") # ADDED
            if not self.ask_target_size(): # Check return status
                self.logger.info("__init__: ask_target_size indicated abort. Application will exit.")
                self.setup_successful = False
                if self.root.winfo_exists(): # Ensure root exists before scheduling destroy
                    self.root.after_idle(self.root.destroy)
                return # Stop further initialization
            
            # Then, if the app hasn't quit from ask_target_size, prompt for initial file/folder
            if self.root.winfo_exists(): # Check if window still exists (it should if we haven't returned)
                # self.prompt_initial_open_choice() # Old call
                if not self.prompt_initial_open_choice(): # Check return status
                    self.logger.info("__init__: prompt_initial_open_choice indicated abort. Application will exit.")
                    self.setup_successful = False
                    if self.root.winfo_exists(): # Ensure root exists before scheduling destroy
                         self.root.after_idle(self.root.destroy)
                    return # Stop further initialization
            
        except Exception as e:
            # Ensure logger is available or use print
            log_message = f"Error initializing application: {str(e)}"
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(log_message) # Changed from warning to error for init failures
                self.logger.error(traceback.format_exc())
            else:
                print(log_message)
                print(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to initialize application: {str(e)}")
            self.setup_successful = False # Mark setup as failed
            if hasattr(self, 'root') and self.root and self.root.winfo_exists(): # Check root before destroying
                 self.root.after_idle(self.root.destroy) # Attempt to close cleanly on error

    def prompt_initial_open_choice(self):
        """Handles the initial prompt to open a file or folder during startup.
           If the user cancels and no images are loaded, the application will exit gracefully."""
        self.prompt_open_file_or_folder() # This will show the dialog and potentially load images

        # After the dialog, if no images were loaded (user cancelled everything)
        # and it's still the initial setup (no current_image loaded yet),
        # then inform the user and prepare to exit.
        if not self.image_paths and self.current_image is None:
            if self.root.winfo_exists(): # Check if root window still exists
                messagebox.showinfo("Exiting", "No image or folder selected. The application will now exit.", parent=self.root)
                # self.root.quit() # Old direct quit
                return False # Indicate abort
        return True # Indicate success or continue

    def activate_eyedropper(self, event=None):
        """Activate eyedropper mode for color picking."""
        try:
            self.eyedropper_active = True
            self.root.title("Image Resizer [Eyedropper Active]")
            if hasattr(self, 'bg_color_label') and self.bg_color_label:
                self.bg_color_label.config(text="🎯 Pick Color", bg="yellow")
            self.logger.info("Eyedropper mode activated")
            
        except Exception as e:
            self.logger.warning(f"Error activating eyedropper: {str(e)}")

    def cancel_eyedropper(self, event=None):
        """Cancel eyedropper mode."""
        try:
            if self.eyedropper_active:
                self.eyedropper_active = False
                self.root.title("Image Resizer")
                # Use the centralized method to update the display
                self.update_bg_color_display()
                self.logger.info("Eyedropper mode cancelled")
                
        except Exception as e:
            self.logger.warning(f"Error cancelling eyedropper: {str(e)}")

    def pick_bg_color(self, x, y=None):
        """Pick background color from the image at the given coordinates."""
        try:
            if not self.current_image:
                return
                
            # Convert canvas coordinates to image coordinates
            # If x is an event object, pass it directly; otherwise pass x,y
            if y is None and hasattr(x, 'x') and hasattr(x, 'y'):
                # We have an event object
                img_x, img_y = self.correct_coordinates(x)
            else:
                # We have separate x,y coordinates
                if y is None:
                    y = 0  # Provide a default y if none was given
                img_x, img_y = self.correct_coordinates(x, y)
            
            # Check if coordinates are within image bounds
            if (0 <= img_x < self.current_image.width and 
                0 <= img_y < self.current_image.height):
                # Get the color at the clicked position
                self.bg_color = self.current_image.getpixel((img_x, img_y))
                
                # Update the color label using the centralized method
                self.update_bg_color_display()
                
                # Exit eyedropper mode
                self.cancel_eyedropper()
                
                self.logger.info(f"Background color picked: {self.bg_color}")
                
        except Exception as e:
            self.logger.warning(f"Error picking background color: {str(e)}")
            self.logger.warning(traceback.format_exc())

    def update_bg_color_label(self):
        """Update the background color label appearance and layout."""
        self.update_bg_color_display()

    def reset_background_color(self, event=None):
        """Reset the background color to white."""
        try:
            self.bg_color = (255, 255, 255, 255)  # White (now RGBA)
            self.update_bg_color_label()
            self.logger.info("Background color reset to white")
            
        except Exception as e:
            self.logger.warning(f"Error resetting background color: {str(e)}")

    def toggle_auto_center(self, event=None):
        """Toggle automatic center selection."""
        try:
            self.auto_center = not self.auto_center
            
            if self.auto_center and self.current_image:
                # Get the center coordinates
                center_x = self.current_image.width // 2
                center_y = self.current_image.height // 2
                
                # Handle the crop click at the center
                self.handle_crop_click(center_x, center_y)
                
            self.logger.info(f"Auto center toggled to {self.auto_center}")
            
        except Exception as e:
            self.logger.warning(f"Error toggling auto center: {str(e)}")

    def setup_logging(self):
        """Setup logging system with both file and console output."""
        # Create a logging window
        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("Debug Console")
        self.log_window.geometry("800x400")
        self.log_window.withdraw()  # Start hidden
        self.log_window.protocol("WM_DELETE_WINDOW", self.log_window.withdraw) # <<< ADDED protocol handler
        
        # Create text widget for logging
        self.log_text = tk.Text(self.log_window, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # --- ADDED: Frame for buttons at the bottom of the log window ---
        button_frame_log = ttk.Frame(self.log_window)
        button_frame_log.pack(fill=tk.X, side=tk.BOTTOM, pady=5)

        def copy_log_to_clipboard():
            try:
                log_content = self.log_text.get(1.0, tk.END)
                self.root.clipboard_clear()
                self.root.clipboard_append(log_content)
                # Optional: give user feedback (e.g., change button text briefly)
                copy_button.config(text="Copied!")
                self.log_window.after(1500, lambda: copy_button.config(text="Copy to Clipboard") if copy_button.winfo_exists() else None)
                self.logger.info("Debug log copied to clipboard.")
            except Exception as e_copy:
                self.logger.error(f"Failed to copy log to clipboard: {e_copy}")
                # Fallback for error during copy
                copy_button.config(text="Copy Failed")
                self.log_window.after(1500, lambda: copy_button.config(text="Copy to Clipboard") if copy_button.winfo_exists() else None)

        copy_button = ttk.Button(button_frame_log, text="Copy to Clipboard", command=copy_log_to_clipboard)
        copy_button.pack(side=tk.RIGHT, padx=10)
        # --- END ADDED ---
        
        # Create a string buffer to capture log output
        self.log_buffer = StringIO()
        
        # Setup logging
        self.logger = logging.getLogger('ImageResizer')
        self.logger.setLevel(logging.DEBUG)
        
        # Create handlers
        console_handler = logging.StreamHandler(self.log_buffer)
        file_handler = logging.FileHandler('resizer_debug.log')
        
        # Create formatters
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        # Add a method to update the log window
        def update_log():
            try:
                # Only update if the log window and text widget both exist
                if hasattr(self, 'log_window') and self.log_window and self.log_window.winfo_exists() and \
                   hasattr(self, 'log_text') and self.log_text and self.log_text.winfo_exists():
                    self.log_text.delete(1.0, tk.END)
                    self.log_text.insert(tk.END, self.log_buffer.getvalue())
                    self.log_text.see(tk.END)
                # Continue updating regardless
                self.root.after(100, update_log)
            except Exception as e:
                # If there's an error, try again later but don't crash
                print(f"Error updating log: {str(e)}")
                self.root.after(1000, update_log)  # Longer delay to avoid spamming errors
        
        # Start updating the log window
        self.root.after(100, update_log)
        
        # Add a method to toggle the log window
        def toggle_log_window():
            if self.log_window.state() == 'withdrawn':
                self.log_window.deiconify()
            else:
                self.log_window.withdraw()
        
        # Add debug menu to the main menu bar
        self.debug_menu = tk.Menu(self.root)
        self.root.config(menu=self.debug_menu)
        self.debug_menu.add_command(label="🛠️ Toggle Debug Console", command=toggle_log_window)

    def handle_error(self, error, context=""):
        """Handle errors and log them with context."""
        error_msg = f"Error in {context}: {str(error)}"
        self.logger.error(error_msg)
        self.logger.error(traceback.format_exc())
        messagebox.showerror("Error", f"{error_msg}\n\nCheck the debug console for details.")
        self.log_window.deiconify()  # Show the debug console

    def create_menu(self):
        """Create the application menu."""
        try:
            print("DEBUG create_menu: Start") # ADDED
            # Create the menu bar
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # File menu
            print("DEBUG create_menu: Before File menu") # ADDED
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="📁 File", menu=file_menu)
            file_menu.add_command(label="📂 Open...", command=self.prompt_open_file_or_folder)
            file_menu.add_separator()
            file_menu.add_command(label="📏 Change Resolution...", command=self.ask_target_size)
            file_menu.add_command(label="📁 Change Output Folder...", command=self.change_output_folder)
            file_menu.add_separator()
            file_menu.add_command(label="❌ Exit", command=self.root.quit)
            print("DEBUG create_menu: After File menu") # ADDED
            
            # Options menu
            print("DEBUG create_menu: Before Options menu") # ADDED
            options_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="⚙️ Options", menu=options_menu)
            
            # Grid submenu
            grid_menu = tk.Menu(options_menu, tearoff=0)
            options_menu.add_cascade(label="🌐 Grid", menu=grid_menu)
            grid_menu.add_checkbutton(label="📏 Show Grid", variable=self.show_grid_var, command=self.toggle_grid)
            grid_menu.add_separator()
            grid_menu.add_command(label="🎨 Change Grid Color...", command=self.grid_color_dialog)
            
            # Mouse submenu with Crosshair submenu
            mouse_menu = tk.Menu(options_menu, tearoff=0)
            options_menu.add_cascade(label="🖱️ Mouse", menu=mouse_menu)
            mouse_menu.add_command(label="🖱️ Change Mouse Mode...", command=self.mouse_mode_dialog)
            
            # Crosshair options - simplified menu with dialog
            mouse_menu.add_separator()
            mouse_menu.add_checkbutton(label="👁️ Show Crosshair", variable=self.show_crosshair_var, command=self.toggle_crosshair)
            mouse_menu.add_command(label="🔧 Crosshair Options...", command=self.crosshair_options_dialog)
            
            # Color Box menu
            color_box_menu = tk.Menu(options_menu, tearoff=0)
            options_menu.add_cascade(label="🎨 Color Box", menu=color_box_menu)
            color_box_menu.add_checkbutton(label="Show Color Box", variable=self.bg_color_toggle_var, command=lambda: self.toggle_bg_color_box())
            color_box_menu.add_separator()
            color_box_menu.add_command(label="Change Settings...", command=self.bg_color_settings_dialog)
            
            # Preview menu
            print("DEBUG create_menu: Before Preview menu") # ADDED
            preview_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="🔍 Preview", menu=preview_menu)
            print("DEBUG create_menu: Before Preview radiobuttons") # ADDED
            preview_menu.add_radiobutton(label="❌ Off", variable=self.preview_mode_var, value="Off", command=self.on_preview_mode_change)
            preview_menu.add_radiobutton(label="🖼️ Show Last Output", variable=self.preview_mode_var, value="Show Last Output", command=self.on_preview_mode_change)
            preview_menu.add_radiobutton(label="👁️ Show Crop Preview", variable=self.preview_mode_var, value="Show Crop Preview", command=self.on_preview_mode_change)
            print("DEBUG create_menu: After Preview radiobuttons") # ADDED
            preview_menu.add_separator()
            
            # --- Commands to open settings dialogs ---
            preview_menu.add_command(label="⚙️ Crop Preview Settings...", command=self.open_crop_preview_settings)
            preview_menu.add_command(label="⚙️ Last Output Settings...", command=self.open_last_output_settings)

            # --- Explicitly update after adding core preview options ---
            print("DEBUG create_menu: Before first update_idletasks") # ADDED
            self.root.update_idletasks()
            print("DEBUG create_menu: After first update_idletasks") # ADDED
            # ----------------------------------------------------------
            
            # These will be populated later with resolution-specific options
            self.preview_mode_menu = preview_menu
            print("DEBUG create_menu: Before update_preview_mode_menu") # ADDED
            self.update_preview_mode_menu()
            print("DEBUG create_menu: After update_preview_mode_menu") # ADDED
            
            # Help menu
            print("DEBUG create_menu: Before Help menu") # ADDED
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="❓ Help", menu=help_menu)
            help_menu.add_command(label="📊 Show Statistics", command=self.show_statistics)
            help_menu.add_command(label="📒 Manual", command=self.show_manual)
            help_menu.add_separator()
            help_menu.add_command(label="🛠️ Toggle Debug Console", command=self.toggle_log_window)
            print("DEBUG create_menu: After Help menu") # ADDED
            
            # Store menu references
            self.file_menu = file_menu
            self.options_menu = options_menu
            self.preview_menu = preview_menu
            self.mouse_menu = mouse_menu
            
            # Force update of the menu
            print("DEBUG create_menu: Before second update_idletasks") # ADDED
            self.root.update_idletasks()
            print("DEBUG create_menu: After second update_idletasks") # ADDED
            
            self.logger.info("Menu created successfully")
            print("DEBUG create_menu: End") # ADDED
            
        except Exception as e:
            self.logger.warning(f"Error creating menu: {str(e)}")

    def toggle_log_window(self):
        """Toggle the visibility of the debug console."""
        if self.log_window.state() == 'withdrawn':
            self.log_window.deiconify()
        else:
            self.log_window.withdraw()

    def update_crosshair_menu_state(self):
        """Update the state of crosshair menu items."""
        try:
            if not hasattr(self, 'crosshair_menu') or not self.crosshair_menu:
                return
                
            if self.show_crosshair_var.get():
            # Enable all crosshair mode options
                try:
                    for i in range(1, 3):  # Enable options 1 and 2
                        self.crosshair_menu.entryconfig(i, state="normal")
                except:
                    # Silently ignore errors if menu doesn't have these items yet
                    pass
                    self.canvas.bind("<Motion>", self.on_mouse_move)
                else:
            # Disable all crosshair mode options
                    try:
                        for i in range(1, 3):  # Disable options 1 and 2
                            self.crosshair_menu.entryconfig(i, state="disabled")
                    except:
                    # Silently ignore errors if menu doesn't have these items yet
                        pass
                        self.canvas.unbind("<Motion>")
                        self.clear_crosshair()
        except Exception as e:
            # Log the error but don't crash
            if hasattr(self, 'logger') and self.logger:
                self.logger.warning(f"Error updating crosshair menu state: {str(e)}")
            else:
                print(f"Error updating crosshair menu state: {str(e)}")

    def clear_crosshair(self):
        """Clear all crosshair elements."""
        for crosshair_id in self.last_crosshair_ids:
            self.canvas.delete(crosshair_id)
        self.last_crosshair_ids = []

    def toggle_crosshair(self):
        """Toggle the crosshair visibility."""
        # Since we no longer have a separate crosshair menu,
        # just toggle the visibility and handle mouse movement
        if self.show_crosshair_var.get():
            # Enable crosshair - enable mouse motion tracking
            self.canvas.bind("<Motion>", self.on_mouse_move)
        else:
            # Disable crosshair - unbind and clear
            self.clear_crosshair()
        
        # Update the display
        self.root.update_idletasks()

    def update_crosshair(self):
        """Update the crosshair based on current mode."""
        if self.show_crosshair_var.get():
            # Force mouse motion update to refresh crosshair
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.event_generate("<Motion>") # Removed warp=True
                
        # Update the display
        self.root.update_idletasks()

    def toggle_hex_label(self):
        """Toggle display of hex color code in the label."""
        # Toggle the state
        self.show_hex_in_label = not self.show_hex_in_label
        print(f"Hex display toggled: {self.show_hex_in_label}")
        
        # Update display
        self.update_bg_color_display()

    def update_bg_color_display(self):
        """Update both the background color label and frame layout."""
        print(f"DEBUG: update_bg_color_display called, position={self.bg_color_box_position}")
        try:
            # Update the label appearance if it exists
            if hasattr(self, 'bg_color_label') and self.bg_color_label and self.bg_color_label.winfo_exists():
                # Update text based on hex display setting
                if self.show_hex_in_label:
                    text = f"HEX: {self.rgb_to_hex(self.bg_color)}"
                else:
                    text = "Background Color"
                
                # Get contrasting text color
                text_color = self.get_contrasting_text_color(self.bg_color)
                
                # Update the label
                self.bg_color_label.config(
                    text=text,
                    bg=self.rgb_to_hex(self.bg_color),
                    fg=text_color
                )
        
            # Update reset button if it exists
            if hasattr(self, 'bg_color_reset') and self.bg_color_reset and self.bg_color_reset.winfo_exists():
                # Make the reset button magenta but keep text color detection system
                magenta_color = "#FF00FF"
                self.bg_color_reset.config(  # <--- Indent this line
                    bg=magenta_color,
                    fg="white" if self.is_dark_color(magenta_color) else "black"
                ) # <--- and this line (and the one in between)
            
            # Force update of the layout
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"ERROR updating bg_color display: {str(e)}")
            if hasattr(self, 'logger'):
                self.logger.error(f"Error updating bg_color display: {str(e)}")
                
            # If update failed and widgets don't exist, try to recreate them
            if (not hasattr(self, 'bg_color_label') or 
                not self.bg_color_label or 
                not self.bg_color_label.winfo_exists()):
                # Recreate the color box if it should be visible
                if self.bg_color_toggle_var.get():
                    print("DEBUG: Recreating color box since update failed")
                    self.adjust_frames()
        
    def toggle_bg_color_box(self, init=False):
        """Toggle the background color box visibility."""
        if not init:
            self.bg_color_toggle_var.set(not self.bg_color_toggle_var.get())
        
        # Update the menu state
        self.update_menu_states()
        
        # Update the display
        self.update_bg_color_display()

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

    def switch_mouse_mode(self, event=None):
        """Switch between mouse click action modes."""
        try:
            # Cycle through modes: (L:Center, R:BG) -> (L:BG, R:Center)
            if self.left_click_mode == "center":
                self.left_click_mode = "background"
                self.right_click_mode = "center"
            else: # Assumes L:BG, R:Center (or should transition to L:Center, R:Background)
                self.left_click_mode = "center"
                self.right_click_mode = "background" # <<< MOVED INTO ELSE BLOCK

            # Update the dialog if open
            if self.mouse_window and self.mouse_window.winfo_exists():
                 if self.mode_label and self.mode_label.winfo_exists():
                      self.mode_label.config(text=self.get_mouse_mode_text())

            self.logger.info(f"Mouse mode switched to Left={self.left_click_mode}, Right={self.right_click_mode}")
        except Exception as e:
            self.logger.warning(f"Error switching mouse mode: {str(e)}")
            
    def ask_target_size(self):
        # This is one of the methods that appeared duplicated in the original file.
        # Ensuring a single, correct version is restored.
        global TARGET_SIZE
        picker = ResolutionPicker(self.root) # Assuming ResolutionPicker is correctly defined/imported
        picker.withdraw() # Hide initially to prevent flicker
        # Make picker modal to the root window
        picker.transient(self.root)
        picker.grab_set()

        # Center the picker dialog on the screen
        picker.update_idletasks() # Allow picker to calculate its own required size
        width = picker.winfo_width()
        height = picker.winfo_height()

        screen_w = picker.winfo_screenwidth()
        screen_h = picker.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)

        picker.geometry(f"{width}x{height}+{x}+{y}")

        # NOTE: ResolutionPicker should ideally position itself (e.g., center on parent)
        # in its __init__ method before this deiconify call.
        picker.deiconify() # Show it now that it's configured
        self.root.wait_window(picker) # Wait for picker dialog to close

        if picker.result:
            TARGET_SIZE = picker.result
            self.update_preview_mode_menu() # Update preview options if resolutions change
            self.root.update_idletasks()
            current_width = self.root.winfo_width()
            if current_width < 400:
                self.root.geometry(f"400x{self.root.winfo_height()}")
            if self.current_image is not None: # If processing already started
                messagebox.showinfo("Resolution Updated",
                    f"Selected {len(TARGET_SIZE)} resolution(s):\n"
                    + "\n".join(f"{w}x{h}" for w, h in TARGET_SIZE), parent=self.root)
            return True # Indicate success
        else: # Picker was cancelled
             if self.current_image is None and not TARGET_SIZE: # No image loaded AND no target sizes set from before
                 self.logger.info("ask_target_size: Picker cancelled on initial launch with no prior TARGET_SIZE. Aborting.")
                 # Ensuring self.root is still valid before quitting
                 if self.root and self.root.winfo_exists():
                    # self.root.quit() # Old direct quit
                    return False # Indicate abort
             else:
                  self.logger.info("ask_target_size: Picker cancelled, but continuing with existing TARGET_SIZE or loaded image.")
                  if TARGET_SIZE: # Only show warning if there was a previous setting
                    messagebox.showwarning("Resolution Not Changed", "Resolution selection was cancelled. Using previous settings.", parent=self.root)
             return True # Indicate continue even if warning was shown

    def show_image(self):
        if not self.image_paths:
            return
        img_path = self.image_paths[self.current_index]
        self.current_image = Image.open(img_path).convert("RGBA")

        self.display_image = self.current_image.copy()

        screen_width = self.root.winfo_screenwidth() - 100
        screen_height = self.root.winfo_screenheight() - 100
        max_display_size = (screen_width, screen_height)

        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.ANTIALIAS

        # First create the base thumbnail
        self.display_image.thumbnail(max_display_size, resample_filter)

        # Store the base size for zoom calculations
        self.base_width = self.display_image.width
        self.base_height = self.display_image.height

        # Apply zoom
        if self.zoom_level != 1.0:
            new_width = int(self.base_width * self.zoom_level)
            new_height = int(self.base_height * self.zoom_level)
            # Ensure minimum size of 1x1 for resized image
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            self.display_image = self.display_image.resize((new_width, new_height), resample_filter)

        try:
            self.tk_image = ImageTk.PhotoImage(self.display_image)
            self.canvas.delete("all")

            # Update the display including both canvas and bg color label
            self.update_bg_color_display()

            # Get the current canvas size
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()

            # Calculate center position with scroll offset
            self.image_x = canvas_w // 2 + self.scroll_x
            self.image_y = canvas_h // 2 + self.scroll_y

            # Create image at center position
            self.canvas.create_image(self.image_x, self.image_y, anchor=tk.CENTER, image=self.tk_image)

            # Update the grid if it's enabled
            if self.show_grid_var.get():
                self.update_grid()
            
            # Force update of the display
            self.root.update_idletasks()
            self.root.update()
            
        except Exception as e:
            self.logger.error(f"Error in show_image during PhotoImage creation or display: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.tk_image = None # Ensure tk_image is None if it failed
            self.canvas.delete("all") # Clear canvas
            # Optionally display an error message on the canvas
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            if canvas_w > 0 and canvas_h > 0: # Check if canvas has valid dimensions
                 self.canvas.create_text(
                     canvas_w / 2, 
                     canvas_h / 2, 
                     text="Error displaying image.\\nCheck debug console (Ctrl+D) or resizer_debug.log.", 
                     fill="red", 
                     justify=tk.CENTER
                 )
            return # Early exit if image display fails critically

    def handle_mouse_click(self, event):
        """Handle mouse clicks based on current mode."""
        if not self.current_image:
            if self.eyedropper_active:
                self.cancel_eyedropper() # Cancel eyedropper if it was active with no image
            self.logger.info("Mouse click ignored: No image loaded.")
            return

        # Get image coordinates from the event
        img_x, img_y = self.correct_coordinates(event)

        if img_x is None or img_y is None:
            self.logger.warning("Mouse click ignored: Could not determine image coordinates.")
            if self.eyedropper_active: # Still cancel eyedropper if it was active
                self.cancel_eyedropper()
            return

        if self.eyedropper_active:
            # For eyedropper, pass the event object directly
            self.pick_bg_color(event)
            return

        # Check if coordinates are within image bounds for regular clicks
        if (0 <= img_x < self.current_image.width and
            0 <= img_y < self.current_image.height):

            action_taken = ""
            if event.num == 1:  # Left click
                if self.left_click_mode == "center":
                    self.handle_crop_click(img_x, img_y) # Call the correct function
                    action_taken = f"handle_crop_click with left_click_mode='center'"
                elif self.left_click_mode == "background":
                    self.handle_background_click(img_x, img_y)
                    action_taken = f"handle_background_click with left_click_mode='background'"
                # Add other left modes if needed

            elif event.num == 3:  # Right click
                if self.right_click_mode == "center":
                    self.handle_crop_click(img_x, img_y) # Call the correct function
                    action_taken = f"handle_crop_click with right_click_mode='center'"
                elif self.right_click_mode == "background":
                    self.handle_background_click(img_x, img_y)
                    action_taken = f"handle_background_click with right_click_mode='background'"
                # Add other right modes if needed
            
            if action_taken:
                 self.logger.info(f"Mouse button {event.num} click at image ({img_x}, {img_y}): called {action_taken}.")
            else:
                 self.logger.info(f"Mouse button {event.num} click at image ({img_x}, {img_y}): No action configured for current mode (L:'{self.left_click_mode}', R:'{self.right_click_mode}').")
        else:
            self.logger.info(f"Mouse click at image ({img_x}, {img_y}) is outside image bounds ({self.current_image.width}x{self.current_image.height}). Ignored.")
            
        # Removed redundant try/except block that was here

    def handle_crop_click(self, x, y):
        """Handle crop point selection."""
        try: # Outer try block
            if not self.current_image:
                return

            print(f"DEBUG handle_crop_click: Processing image {self.current_index + 1} with coords ({x}, {y})")

            # >>> ADDED DEBUG PRINTS <<<
            print("DEBUG handle_crop_click: --- About to call self.process_image ---")
            process_result = self.process_image(x, y)
            print(f"DEBUG handle_crop_click: --- process_image returned: {process_result} (Type: {type(process_result)}) ---")
            print("DEBUG handle_crop_click: --- About to check 'if process_result:' ---")
            # >>> END DEBUG PRINTS <<<

            # >>> Check if processing was successful <<<
            if process_result:
                # Log successful processing
                self.logger.info(f"Image {self.current_index + 1} processed successfully.")

                # --- Trigger Last Output Preview Update ---
                if self.preview_mode_var.get() == "Show Last Output" and \
                   hasattr(self, 'last_output_window') and self.last_output_window and \
                   self.last_output_window.winfo_exists():

                    print(f"DEBUG handle_crop_click: Triggering update for Last Output Preview.")

                    # Clear existing placeholder or old previews
                    if hasattr(self, 'last_output_previews_frame') and self.last_output_previews_frame.winfo_exists():
                        for widget in self.last_output_previews_frame.winfo_children():
                            widget.destroy() # Remove placeholder/old previews
                    else:
                        print("ERROR handle_crop_click: last_output_previews_frame missing.")
                        # Consider adding error handling or trying to recreate the frame if needed

                    # Reset preview_windows dictionary for this mode (holds the Frame widgets)
                    self.preview_windows = {}

                    # Populate with new previews and calculate required size
                    max_width = 0
                    total_height = 0
                    padding = 20 # Padding between preview frames

                    # Use TARGET_SIZE directly
                    if 'TARGET_SIZE' in globals() and isinstance(TARGET_SIZE, (list, tuple)):
                        for res_w, res_h in TARGET_SIZE: # Use different variable names
                            # This call populates the self.last_output_previews_frame
                            self.update_last_output_preview(res_w, res_h) # Use res_w, res_h

                            # Track estimated dimensions for resizing
                            frame_key = (res_w, res_h)
                            if frame_key in self.preview_windows and self.preview_windows[frame_key].winfo_exists():
                                # Estimate size
                                est_frame_width = res_w + 22  # Approx canvas + padding/border
                                est_frame_height = res_h + 52 # Approx canvas + label + padding/border
                                max_width = max(max_width, est_frame_width)
                                total_height += est_frame_height + padding # Add padding between frames
                                print(f"DEBUG handle_crop_click: Frame {res_w}x{res_h} est size: {est_frame_width}x{est_frame_height}. New max_w={max_width}, total_h={total_height}")

                        # Calculate minimum width based on title
                        try:
                            title_font = font.nametofont("TkDefaultFont").copy() # Use imported font
                            min_title_width = title_font.measure(self.last_output_window.title()) + 40
                        except Exception:
                            min_title_width = 200 # Fallback

                        # Calculate final size (adjust total height calculation slightly)
                        final_width = max(max_width + 40, min_title_width) # Add padding/borders
                        final_height = total_height - padding + 40 # Subtract last padding, add border/padding
                        print(f"DEBUG handle_crop_click: Calculated final size: {final_width}x{final_height}")

                        # Apply resize using the safe, delayed method
                        self.apply_geometry_safely(self.last_output_window, final_width, final_height)
                    else:
                        print("ERROR handle_crop_click: TARGET_SIZE not available or not iterable for preview update.")
                # --- END Trigger ---

                # Move to next image
                if self.current_index < len(self.image_paths) - 1:
                    self.current_index += 1
                    self.show_image()
                    self.root.update() # Force update to show next image immediately
                else:
                    messagebox.showinfo("Complete", "All images have been processed!")
                    # Reset to first image
                    self.current_index = 0
                    self.show_image()
                    self.root.update() # Also update after reset
            else:
                # Log failed processing if process_image returns False
                self.logger.warning(f"Image {self.current_index + 1} processing failed for coords ({x}, {y}).")

        except Exception as e: # Catch any unexpected error during the process
            self.logger.warning(f"Error handling crop click: {str(e)}")
            self.logger.error(traceback.format_exc()) # Log detailed traceback
            messagebox.showerror("Processing Error", f"An error occurred while processing the image: {str(e)}")

    def handle_background_click(self, x, y):
        """Handle background click at the specified image coordinates."""
        # This method assumes x, y are already corrected image coordinates
        if not self.current_image:
            return

        # Check if coordinates are valid (redundant check as handle_mouse_click does it, but safe)
        if (0 <= x < self.current_image.width and
            0 <= y < self.current_image.height):
            try:
                self.bg_color = self.current_image.getpixel((x, y))
                self.update_bg_color_display()  # Update the UI element
                self.logger.info(f"Background color set to {self.bg_color} at ({x},{y})")
            except Exception as e:
                self.logger.warning(f"Error getting pixel color: {str(e)}")
        else:
            self.logger.warning(f"Background click coordinates ({x},{y}) out of bounds.")

    def on_mouse_move(self, event):
        """Handle mouse movement for crosshair and preview."""
        if not self.current_image:
            return

        # Get the image coordinates
        img_x, img_y = self.correct_coordinates(event)
        
        if img_x is None or img_y is None:
            self.clear_crosshair() # Clear crosshair if coords are invalid
            # Optionally, you might want to clear or update preview windows to an "invalid coords" state.
            # For now, just returning to avoid processing with bad coordinates.
            self.logger.debug("on_mouse_move: Invalid image coordinates, crosshair cleared.")
            return

        # Handle crosshair
        if self.show_crosshair_var.get():
            self.clear_crosshair()
            
            if self.tk_image and 0 <= img_x < self.current_image.width and 0 <= img_y < self.current_image.height:
                # Snap to the nearest pixel
                snapped_x = int(img_x)
                snapped_y = int(img_y)
                
                # --- Draw based on crosshair type and size ---
                cross_type = self.crosshair_type.get()
                cross_size = 1
                if cross_type == 'cross':
                    try:
                        cross_size = self.crosshair_size.get()
                        if cross_size < 1: cross_size = 1 # Ensure minimum size of 1
                    except tk.TclError:
                        cross_size = 1 # Default to 1 if value is invalid
                
                # Calculate the size of a pixel in canvas coordinates
                pixel_size = max(1, int(self.zoom_level))
                
                # Convert snapped image coordinates back to canvas coordinates
                img_left = self.image_x - (self.tk_image.width() // 2)
                img_top = self.image_y - (self.tk_image.height() // 2)
                
                # --- Helper function to draw a single pixel ---
                def draw_crosshair_pixel(pixel_x, pixel_y):
                    # Check if the pixel is within the image bounds
                    if 0 <= pixel_x < self.current_image.width and 0 <= pixel_y < self.current_image.height:
                        # Get the color at this position
                        try:
                            color = self.current_image.getpixel((pixel_x, pixel_y))
                        except IndexError:
                            return # Skip if out of bounds
                        # Handle potential alpha channel
                        if isinstance(color, tuple) and len(color) == 4:
                            color = color[:3] # Use only RGB
                        elif not isinstance(color, tuple) or len(color) != 3:
                            # print(f"DEBUG: Unexpected color format at ({pixel_x},{pixel_y}): {color}")
                            return # Skip this pixel if color format is wrong
 
                        # Determine crosshair color
                        if self.crosshair_use_negative.get():
                            # Create negative color
                            neg_color = (255 - color[0], 255 - color[1], 255 - color[2])
                            crosshair_color = rgb_to_hex(neg_color)
                            # print(f"DEBUG: Negative Mode: Pixel=({pixel_x},{pixel_y}), OrigColor={color}, NegColor={neg_color}, Hex={crosshair_color}") # DEBUG PRINT
                        else:
                            crosshair_color = self.crosshair_color
                            # print(f"DEBUG: Custom Color Mode: Pixel=({pixel_x},{pixel_y}), Color={crosshair_color}") # DEBUG PRINT
 
                        # --- MODIFIED LOGIC FOR CENTERING ---
                        # Original image dimensions
                        orig_img_width = self.current_image.width
                        orig_img_height = self.current_image.height

                        # Displayed tk_image dimensions
                        tk_img_width = self.tk_image.width()
                        tk_img_height = self.tk_image.height()

                        # Ensure no division by zero if images are not loaded or have zero dimensions
                        if orig_img_width == 0 or orig_img_height == 0 or tk_img_width == 0 or tk_img_height == 0:
                            return 

                        # Actual size of one original image pixel on the canvas
                        actual_scaled_pixel_w = tk_img_width / orig_img_width
                        actual_scaled_pixel_h = tk_img_height / orig_img_height

                        # Top-left coordinate of the image on the canvas
                        img_left_on_canvas = self.image_x - (tk_img_width // 2)
                        img_top_on_canvas = self.image_y - (tk_img_height // 2)
                        
                        # Offset of the target image pixel (pixel_x, pixel_y) from the top-left of the original image, 
                        # scaled to the display image, giving the top-left of the scaled pixel on the tk_image.
                        canvas_offset_x_in_tk_image = (pixel_x / orig_img_width) * tk_img_width
                        canvas_offset_y_in_tk_image = (pixel_y / orig_img_height) * tk_img_height

                        # Top-left coordinate of the specific (pixel_x, pixel_y) on the canvas
                        top_left_canvas_x = img_left_on_canvas + canvas_offset_x_in_tk_image
                        top_left_canvas_y = img_top_on_canvas + canvas_offset_y_in_tk_image
                        
                        # Center coordinate of the specific (pixel_x, pixel_y)'s scaled representation on the canvas
                        center_scaled_pixel_cx = top_left_canvas_x + actual_scaled_pixel_w / 2
                        center_scaled_pixel_cy = top_left_canvas_y + actual_scaled_pixel_h / 2

                        # Size of the visual mark to draw (current crosshair pixel drawing logic)
                        draw_mark_size = max(1, int(self.zoom_level))

                        # Calculate corners for the mark, centered on the center of the scaled image pixel
                        x0 = center_scaled_pixel_cx - draw_mark_size / 2
                        y0 = center_scaled_pixel_cy - draw_mark_size / 2
                        x1 = center_scaled_pixel_cx + draw_mark_size / 2
                        y1 = center_scaled_pixel_cy + draw_mark_size / 2
                        # --- END MODIFIED LOGIC ---
 
                        crosshair_id = self.canvas.create_rectangle(
                            x0, y0, x1, y1,
                            fill=crosshair_color,
                            outline="" # No outline for single pixels
                        )
                        self.last_crosshair_ids.append(crosshair_id)
                # --- End Helper function ---
 
                # --- Draw based on type ---
                if cross_type == 'pixel':
                    draw_crosshair_pixel(snapped_x, snapped_y)
                elif cross_type == 'cross':
                    # Draw center pixel
                    draw_crosshair_pixel(snapped_x, snapped_y)
                    # Draw arms based on size
                    for i in range(1, cross_size + 1):
                        draw_crosshair_pixel(snapped_x, snapped_y - i) # Up
                        draw_crosshair_pixel(snapped_x, snapped_y + i) # Down
                        draw_crosshair_pixel(snapped_x - i, snapped_y) # Left
                        draw_crosshair_pixel(snapped_x + i, snapped_y) # Right
                # --- End Draw based on type ---

        # Handle preview updates
        if self.eyedropper_active:
            return

        # Update preview windows
        # self.update_preview_windows(img_x, img_y) # OLD CALL
        if self.preview_mode_var.get() == "Show Crop Preview":
            self._update_all_crop_previews_based_on_dialog(img_x, img_y) # NEW CALL

    def update_preview_windows(self, center_x=None, center_y=None):
        """This method is now primarily a wrapper or can be deprecated if 
           _update_all_crop_previews_based_on_dialog fully covers its original intent for mouse move.
           For now, it directly calls the dialog-aware update method.
        """
        # --- Guard: Return if no image or coords are invalid/outside image bounds ---
        # This initial guard is still useful.
        if not self.current_image or center_x is None or center_y is None or \
           not (0 <= center_x < self.current_image.width and 0 <= center_y < self.current_image.height):
            # If outside bounds, we might want to explicitly hide/clear live crop previews.
            # For now, _update_all_crop_previews_based_on_dialog has logic to handle this.
            self.logger.debug("update_preview_windows: called with invalid coords or no image, delegating to _update_all_crop_previews_based_on_dialog which should handle this.")
            # Pass through to ensure any cleanup logic in the called method is triggered for out-of-bounds.
            if self.preview_mode_var.get() == "Show Crop Preview":
                 self._update_all_crop_previews_based_on_dialog(center_x, center_y)
            return 
        
        if self.preview_mode_var.get() == "Show Crop Preview":
            self.logger.debug(f"update_preview_windows: delegating to _update_all_crop_previews_based_on_dialog for {center_x},{center_y}")
            self._update_all_crop_previews_based_on_dialog(center_x, center_y)
        else:
            self.logger.debug("update_preview_windows: Called when not in Show Crop Preview mode, doing nothing.")


    def close_preview_window(self, idx):
        # This method was likely for the old menu-based checkboxes for crop previews.
        # With dialogs, closing is handled by _handle_single_crop_Toplevel_closed_by_user or dialog close.
        # Keeping it for now in case it's referenced, but it might be dead code.
        self.logger.warning(f"close_preview_window({idx}) called - this might be deprecated with dialog system.")
        if hasattr(self, 'preview_windows') and idx in self.preview_windows:
            window = self.preview_windows.get(idx)
            if isinstance(window, tk.Toplevel) and window.winfo_exists():
                try: window.destroy()
                except tk.TclError: pass
            del self.preview_windows[idx]
            # Uncheck the corresponding checkbox in the dialog if it exists
            if hasattr(self, 'crop_preview_dialog_vars') and idx < len(self.crop_preview_dialog_vars):
                self.crop_preview_dialog_vars[idx].set(False)

    def destroy_preview_window(self):
        # This method name is a bit generic. It was likely intended to close all preview stuff.
        # destroy_all_preview_related_windows() is now the comprehensive method.
        self.logger.warning("destroy_preview_window() called - consider using destroy_all_preview_related_windows() if a full cleanup is intended.")
        self.destroy_all_preview_related_windows()
        # If this was tied to a specific mode (e.g. Show Crop Preview), also set mode to Off.
        # For now, just calls the more comprehensive cleanup.

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
        self.logger.info(f"prev_image called. Current index before: {self.current_index}, Image paths count: {len(self.image_paths)}")
        if self.image_paths and self.current_index > 0:
            self.current_index -= 1
            self.logger.info(f"prev_image: New index: {self.current_index}")
            self.show_image()
        else:
            self.logger.info(f"prev_image: Condition not met. Current index: {self.current_index}, Image paths count: {len(self.image_paths)}")

    def update_menu_states(self):
        if hasattr(self, 'bg_color_menu'):
            # Update the state of Toggle Hex Color and Change Location menu items
            self.bg_color_menu.entryconfig(1, state="normal" if self.bg_color_toggle_var.get() else "disabled")  # Toggle Hex Color
            self.bg_color_menu.entryconfig(2, state="normal" if self.bg_color_toggle_var.get() else "disabled")  # Change Location
            
            # Update the state of the Toggle BG Color Box menu item
            self.bg_color_menu.entryconfig(0, state="normal")  # Toggle BG Color Box

    def adjust_frames(self):
        """Adjust the layout of frames and widgets using explicit packing."""
        # --- Ensure default position exists EARLY --- 
        if not hasattr(self, 'bg_color_box_position') or self.bg_color_box_position is None:
            print("DEBUG adjust_frames: Initializing missing bg_color_box_position to 'top'")
            self.bg_color_box_position = "top"
        # --- End Ensure default ---
        
        print(f"DEBUG: adjust_frames called, bg_color_box_position={self.bg_color_box_position}")
            
        # --- Explicit Cleanup --- 
        if hasattr(self, 'color_container') and self.color_container:
            try:
                self.color_container.destroy() # Ignore error if already destroyed
            except tk.TclError:
                pass # Widget already destroyed
            self.color_container = None
            self.bg_color_label = None # Reset internal widget refs too
            self.bg_color_reset = None
        if hasattr(self, 'canvas') and self.canvas:
            try: self.canvas.pack_forget()
            except tk.TclError: pass
        # --- End Cleanup --- 

        position = str(self.bg_color_box_position).lower()
        if position not in ["top", "bottom"]: position = "top"
        print(f"DEBUG: Using position: {position}")

        created_color_container = None
        if self.bg_color_toggle_var.get():
            created_color_container = self.create_color_box_widgets() # New helper creates widgets

        # Fallback: If color box should be visible but not created, try to recreate and pack it
        if self.bg_color_toggle_var.get() and not created_color_container:
            print("DEBUG: Fallback - recreating color box widgets after position change")
            created_color_container = self.create_color_box_widgets()
            if created_color_container:
                # Pack in the correct position
                if position == "top":
                    created_color_container.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                else:
                    created_color_container.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        # 2. Pack elements in the desired order
        if position == "top":
            if created_color_container: # Pack color box first if top
                created_color_container.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            if hasattr(self, 'canvas') and self.canvas: # Then canvas filling rest
                    self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        elif position == "bottom":
            if hasattr(self, 'canvas') and self.canvas: # Canvas first filling space
                    self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            if created_color_container: # Color box last at bottom
                created_color_container.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

                self.root.update_idletasks()
                print("DEBUG: UI update completed successfully")

    def create_color_box_widgets(self):
        """Creates the color box widgets and returns the container frame (DOES NOT PACK)."""
        try:
            # Create the main container frame that will hold everything
            # IMPORTANT: Store the container reference in self.color_container
            self.color_container = ttk.Frame(self.root)
            
            # Create a frame for the reset button - placed on right
            button_frame = ttk.Frame(self.color_container)
            button_frame.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Add reset button - magenta background, fixed width
            magenta_color = "#FF00FF"
            # IMPORTANT: Store widget reference in self.bg_color_reset
            self.bg_color_reset = tk.Button(
                button_frame,
                text="Reset",
                width=6,
                command=self.reset_bg_color,
                bg=magenta_color,
                fg="white" if self.is_dark_color(magenta_color) else "black"
            )
            self.bg_color_reset.pack(side=tk.RIGHT, padx=(5, 0))
            self.bg_color_reset.bind("<Button-3>", self.show_color_picker_menu)
            
            # Add BG Color label
            if self.show_hex_in_label:
                label_text = f"HEX: {rgb_to_hex(self.bg_color)}"
            else:
                label_text = "Background Color"
            text_color = self.get_contrasting_text_color(self.bg_color)
            # IMPORTANT: Store widget reference in self.bg_color_label
            self.bg_color_label = tk.Label(
                self.color_container, 
                text=label_text, 
                bg=self.rgb_to_hex(self.bg_color),
                fg=text_color,
                relief="sunken",
                bd=1
            )
            self.bg_color_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            # Simplified binding for eyedropper activation
            self.bg_color_label.bind("<Button-1>", lambda e: self.activate_eyedropper())

            print("DEBUG: Color box widgets created successfully (container not packed by this func)")
            return self.color_container # Return the container to be packed by adjust_frames
            
        except Exception as e:
            print(f"ERROR creating color box widgets: {str(e)}")
            if hasattr(self, 'logger'):
                self.logger.error(f"Error creating color box widgets: {str(e)}")
                self.logger.error(traceback.format_exc())
            # Ensure self references are None if creation failed mid-way
            self.color_container = None 
            self.bg_color_label = None
            self.bg_color_reset = None
            return None # Return None on error

    def update_last_output_preview(self, width, height):
        """Update the preview window with the last output image."""
        print(f"DEBUG update_last_output_preview: Updating for {width}x{height}")
        # --- Check if the main container and scrollable frame exist ---
        if not hasattr(self, 'last_output_window') or not self.last_output_window or not self.last_output_window.winfo_exists():
            print(f"DEBUG update_last_output_preview: Last output window does not exist.")
            return
        # --- DELETED: scrollable frame check ---

        try:
            # Get the output path for this resolution
            if not self.image_paths or self.current_index >= len(self.image_paths):
                 print("DEBUG update_last_output_preview: Invalid current_index or no image_paths.")
                 return
            img_path = self.image_paths[self.current_index]
            if not hasattr(self, 'output_folder') or not self.output_folder:
                 print("DEBUG update_last_output_preview: Output folder not set.")
                 return
            # --- MODIFIED: Construct BMP filename for preview ---
            base_filename = os.path.splitext(os.path.basename(img_path))[0]
            bmp_filename = base_filename + ".bmp"
            output_path = os.path.join(self.output_folder, f"{width}x{height}", bmp_filename)
            # --- END MODIFICATION ---
            print(f"DEBUG update_last_output_preview: Checking path: {output_path}")

            # --- Find or Create Frame *within* the designated previews frame --- 
            # Ensure the main container frame for previews exists
            if not hasattr(self, 'last_output_previews_frame') or not self.last_output_previews_frame or not self.last_output_previews_frame.winfo_exists():
                print(f"ERROR update_last_output_preview: The main container frame 'last_output_previews_frame' is missing.")
                return

            frame_key = (width, height)
            resolution_frame = None
            # Use self.preview_windows to store references to these inner frames
            if hasattr(self, 'preview_windows') and frame_key in self.preview_windows:
                 if self.preview_windows[frame_key].winfo_exists():
                     resolution_frame = self.preview_windows[frame_key]
                     print(f"DEBUG update_last_output_preview: Found existing frame for {width}x{height}")
                 else:
                     print(f"DEBUG update_last_output_preview: Frame for {width}x{height} existed but was destroyed. Will recreate.")
                     del self.preview_windows[frame_key] # Remove stale reference
            
            if resolution_frame is None:
                 print(f"DEBUG update_last_output_preview: Creating frame for {width}x{height} inside previews container")
                 # Use the passed parent_frame (last_output_previews_frame)
                 resolution_frame = ttk.Frame(self.last_output_previews_frame, borderwidth=1, relief="solid")
                 # Pack the frame within the parent (e.g., top-to-bottom)
                 resolution_frame.pack(pady=10, padx=10, anchor="n", fill='x', expand=True) # Pack top-to-bottom, expand horizontally
                 # Store the reference
                 if not hasattr(self, 'preview_windows'): self.preview_windows = {}
                 self.preview_windows[frame_key] = resolution_frame
                 # Add label and canvas inside this new frame
                 ttk.Label(resolution_frame, text=f"{width}x{height}").pack(pady=(5, 0)) # Add padding
                 canvas = tk.Canvas(resolution_frame, width=width, height=height, bg='lightgrey')
                 canvas.pack(pady=(0, 5)) # Add padding
                 resolution_frame.canvas = canvas
                 resolution_frame.img = None
            # --- End Frame Creation/Retrieval --- 
                 
            # Get the canvas (it should exist if frame exists)
            if not hasattr(resolution_frame, 'canvas') or not resolution_frame.canvas.winfo_exists():
                 print(f"ERROR update_last_output_preview: Canvas missing for {width}x{height}. Recreating.")
                 # Attempt to recreate
                 for widget in resolution_frame.winfo_children():
                     if isinstance(widget, tk.Canvas): widget.destroy()

            else:
                 canvas = resolution_frame.canvas

            # --- Load and Display Image --- 
            if not os.path.exists(output_path):
                print(f"DEBUG update_last_output_preview: Path does not exist: {output_path}")
                self.logger.warning(f"Last Output Preview: Image file not found at {output_path} for resolution {width}x{height}.") # ADDED LOG
                canvas.delete("all") # Clear the canvas
                canvas.create_text(width/2, height/2, text="Not Found", fill="orange")
                resolution_frame.img = None # Clear reference
            else:
                 print(f"DEBUG update_last_output_preview: Loading image from {output_path}")
                 img = Image.open(output_path)
                 print(f"DEBUG update_last_output_preview: Creating PhotoImage for {width}x{height}")
                 photo = ImageTk.PhotoImage(img)
                 canvas.delete("all")
                 canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                 resolution_frame.img = photo # Keep reference
                 print(f"DEBUG update_last_output_preview: Update display complete for {width}x{height}")
            # --- End Load and Display --- 

            # --- REMOVED Scroll Region Update --- 

        except FileNotFoundError:
            print(f"DEBUG update_last_output_preview: File not found error for {output_path}")
            if 'canvas' in locals() and canvas.winfo_exists(): # Check if canvas exists
                 canvas.delete("all")
                 canvas.create_text(width/2, height/2, text="Not Found", fill="orange")
            if 'resolution_frame' in locals() and resolution_frame.winfo_exists(): # Check if frame exists
                 resolution_frame.img = None
        except Exception as e:
            print(f"ERROR update_last_output_preview: Failed for {width}x{height}: {str(e)}")
            self.logger.error(f"Error updating last output preview for {width}x{height}: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Optionally show error in preview area
            if hasattr(self, 'preview_windows') and (width, height) in self.preview_windows:
                    frame = self.preview_windows[(width, height)]
                    if frame.winfo_exists() and hasattr(frame, 'canvas'):
                        frame.canvas.delete("all")
                        frame.canvas.create_text(width/2, height/2, text="Error", fill="red")
                        frame.img = None


    def update_preview_mode_menu(self):
        if not self.preview_mode_menu:
            return

        try:
            # Find the index of "⚙️ Crop Preview Settings...". 
            # This item is expected to be present when this function is called from create_menu.
            crop_settings_idx = self.preview_mode_menu.index("⚙️ Crop Preview Settings...")
            
            # "⚙️ Last Output Settings..." is expected at crop_settings_idx + 1.
            # Any dynamically added items (which this function aims to clear) would start
            # at index crop_settings_idx + 2.
            
            # Loop as long as the menu contains items beyond "⚙️ Last Output Settings...".
            # The index of "Last Output Settings..." is (crop_settings_idx + 1).
            # So, if index('end') is greater than that, there are dynamic items to remove.
            while self.preview_mode_menu.index('end') > (crop_settings_idx + 1):
                # Delete the item immediately following "Last Output Settings...".
                # This item is at index (crop_settings_idx + 2).
                self.preview_mode_menu.delete(crop_settings_idx + 2)
                # The loop continues, and self.preview_mode_menu.index('end') will be re-evaluated.
                # This ensures progress towards the loop termination condition.

        except tk.TclError:
            # This exception occurs if "⚙️ Crop Preview Settings..." is not found in the menu.
            # This would indicate an unexpected menu structure if called during initial setup.
            # Log a warning and do not attempt to modify the menu to prevent further errors.
            self.logger.warning(
                "update_preview_mode_menu: '⚙️ Crop Preview Settings...' not found. "
                "Cannot clear dynamic menu items. Menu structure might be unexpected."
            )
            # The original 'else' block that handled this case had its own potentially problematic loop.
            # By simply passing here, we avoid that risk if the menu structure is not as assumed.
            pass
        except Exception as e:
            # Catch any other unexpected errors during menu manipulation.
            self.logger.error(f"Unexpected error in update_preview_mode_menu: {e}")
            self.logger.error(traceback.format_exc())

        # self.crop_preview_resolution_vars.clear() # these are now dialog_vars
        # self.last_output_resolution_vars.clear()
        self.root.update_idletasks() # Ensure menu is updated

    def handle_crop_resolution_toggle(self, idx, is_checked):
        """Handles toggling of a crop preview resolution checkbox from the main menu."""
        self.logger.info(f"Crop preview resolution index {idx} toggled to {'checked' if is_checked else 'unchecked'} via menu.")
        # self.crop_preview_resolution_vars[idx] is already updated by Tkinter

        if not is_checked:
            # If unchecked, try to close the corresponding Toplevel preview window
            if hasattr(self, 'preview_windows') and idx in self.preview_windows:
                window_to_close = self.preview_windows.get(idx)
                if isinstance(window_to_close, tk.Toplevel) and window_to_close.winfo_exists():
                    self.logger.info(f"Closing crop preview Toplevel for index {idx} due to menu uncheck.")
                    window_to_close.destroy()
                if idx in self.preview_windows: # Check again before deleting
                    del self.preview_windows[idx]
        else:
            # If checked, the preview window will be created/updated on the next mouse move
            # by update_preview_windows, which should use self.crop_preview_resolution_vars.
            # We can also try to trigger an update now if we have valid last mouse coordinates.
            if self.current_image and hasattr(self, 'cursor_x') and hasattr(self, 'cursor_y') and \
               (0 <= self.cursor_x < self.current_image.width and 0 <= self.cursor_y < self.current_image.height):
                self.logger.info(f"Crop preview for index {idx} checked. Forcing update based on last cursor position.")
                self.update_preview_windows(self.cursor_x, self.cursor_y)
            else:
                self.logger.info(f"Crop preview for index {idx} checked. Will update on next mouse move over image.")

    def _toggle_last_output_single_preview(self, res_w, res_h, is_checked):
        """Handles toggling a single last output preview resolution from the menu."""
        self.logger.info(f"Last output preview for {res_w}x{res_h} toggled to {'checked' if is_checked else 'unchecked'} via menu.")
        # self.last_output_resolution_vars should already reflect this change.

        # This method will primarily control what is SHOWN within the single
        # self.last_output_window. The window itself is managed by on_preview_mode_change.
        if self.preview_mode_var.get() == "Show Last Output" and \
           hasattr(self, 'last_output_window') and self.last_output_window and self.last_output_window.winfo_exists():
            self._refresh_last_output_window_content()
        else:
            self.logger.info("Last output window not active or not found, toggle ignored for now.")

    def _refresh_last_output_window_content(self):
        """Refreshes the content of the last_output_window based on last_output_resolution_vars."""
        if not (hasattr(self, 'last_output_window') and self.last_output_window and self.last_output_window.winfo_exists() and \
                hasattr(self, 'last_output_previews_frame') and self.last_output_previews_frame and self.last_output_previews_frame.winfo_exists()):
            self.logger.info("_refresh_last_output_window_content: Conditions not met.")
            return

        # Clear existing previews in the frame
        for widget in self.last_output_previews_frame.winfo_children():
            widget.destroy()
        # self.preview_windows here refers to the frames *inside* last_output_previews_frame
        self.preview_windows = {} 

        max_width_needed = 0
        total_height_needed = 0
        padding = 20 # Padding between preview frames
        any_preview_shown = False

        if TARGET_SIZE and isinstance(TARGET_SIZE, list) and hasattr(self, 'last_output_resolution_vars'):
            for i, (w, h) in enumerate(TARGET_SIZE):
                if i < len(self.last_output_resolution_vars) and self.last_output_resolution_vars[i].get():
                    any_preview_shown = True
                    self.update_last_output_preview(w, h) # Adds one preview frame to self.last_output_previews_frame
                    
                    # Estimate size contribution for resizing the main last_output_window
                    # These are rough estimates, actual size depends on content and packing
                    est_frame_width = w + 22  # Approx canvas + padding/border
                    est_frame_height = h + 52 # Approx canvas + label + padding/border
                    max_width_needed = max(max_width_needed, est_frame_width)
                    total_height_needed += est_frame_height + padding

        if not any_preview_shown:
             ttk.Label(self.last_output_previews_frame,
                       text="No resolutions selected in the Preview menu.",
                       anchor="center", justify="center").pack(expand=True)
             final_width = 300 # Default size if no previews are shown
             final_height = 100
        else:
            min_title_width = 200 # Fallback for title width
            try:
                # Ensure font is imported if used here
                from tkinter import font as tkFont # Local import for safety
                title_font = tkFont.nametofont("TkDefaultFont").copy()
                min_title_width = title_font.measure(self.last_output_window.title()) + 40
            except Exception: pass

            final_width = max(max_width_needed + 40, min_title_width, 200)
            final_height = max(total_height_needed - padding + 40, 100)
        
        self.logger.info(f"Resizing last_output_window to {final_width}x{final_height} after content refresh.")
        self.apply_geometry_safely(self.last_output_window, final_width, final_height)
        self.last_output_window.update_idletasks()

    def update_preview_image(self, idx, center_x, center_y):
        """Update the preview image for a specific window."""
        self.logger.debug(f"update_preview_image: Called for idx {idx} with coords ({center_x}, {center_y})")

        if idx not in self.preview_windows or not self.preview_windows[idx].winfo_exists():
            self.logger.debug(f"update_preview_image: Window {idx} not found or destroyed (early check).")
            return

        preview_window = self.preview_windows[idx]

        try:
            if not hasattr(preview_window, 'original_width') or not hasattr(preview_window, 'original_height'):
                self.logger.warning(f"update_preview_image: Window {idx} missing original dimensions.")
                try:
                    preview_window.original_width, preview_window.original_height = TARGET_SIZE[idx]
                    self.logger.debug(f"update_preview_image: Recovered dimensions: {preview_window.original_width}x{preview_window.original_height}")
                except (IndexError, TypeError):
                    self.logger.error(f"update_preview_image: Cannot recover dimensions for index {idx}.")
                    return

            if not hasattr(preview_window, 'preview_label') or \
               not preview_window.preview_label.winfo_exists() or \
               not preview_window.winfo_exists():
                self.logger.warning(f"update_preview_image: Window {idx} or its preview_label missing or destroyed. Aborting update.")
                if idx in self.preview_windows:
                    del self.preview_windows[idx]
                if hasattr(self, 'crop_preview_dialog_vars') and idx < len(self.crop_preview_dialog_vars) and self.crop_preview_dialog_vars[idx].get():
                    self.crop_preview_dialog_vars[idx].set(False)
                return

            preview = self.simulate_process_image(center_x, center_y, preview_window.original_width, preview_window.original_height)

            if preview is None:
                self.logger.error("update_preview_image: simulate_process_image returned None.")
                if preview_window.winfo_exists() and preview_window.preview_label.winfo_exists():
                    preview_window.preview_label.configure(text="Error Simulating", image='')
                    preview_window.preview_label.image = None
                return

            # Explicitly master the PhotoImage to the preview_window.
            # This can help in scenarios where the window is being destroyed,
            # potentially raising a TclError more reliably if preview_window is invalid.
            photo = ImageTk.PhotoImage(preview, master=preview_window) 

            if preview_window.winfo_exists() and preview_window.preview_label.winfo_exists():
                preview_window.preview_label.configure(image=photo, text="")
                preview_window.preview_label.image = photo
                self.logger.debug(f"update_preview_image: Label updated for window {idx}")
            else:
                self.logger.warning(f"update_preview_image: Window {idx} or label destroyed before final configure.")

        except tk.TclError as e_tcl:
            self.logger.warning(f"update_preview_image: TclError for window {idx} (likely being destroyed by WM): {str(e_tcl)}")
            if idx in self.preview_windows:
                del self.preview_windows[idx]
            if hasattr(self, 'crop_settings_dialog') and self.crop_settings_dialog and self.crop_settings_dialog.winfo_exists() and \
               hasattr(self, 'crop_preview_dialog_vars') and idx < len(self.crop_preview_dialog_vars):
                if self.crop_preview_dialog_vars[idx].get():
                    self.crop_preview_dialog_vars[idx].set(False)

        except Exception as e_generic:
            self.logger.error(f"Error updating preview image for window {idx}: {str(e_generic)}")
            self.logger.error(traceback.format_exc())
            try:
                if preview_window.winfo_exists() and hasattr(preview_window, 'preview_label') and preview_window.preview_label.winfo_exists():
                    preview_window.preview_label.configure(text="Error", image='')
                    preview_window.preview_label.image = None
            except tk.TclError:
                self.logger.warning(f"update_preview_image: TclError during generic error handling for window {idx}.")

    def simulate_process_image(self, cx, cy, target_w, target_h):
        # cx, cy ARE ALREADY the original image coordinates calculated by correct_coordinates
        print(f"DEBUG simulate_process: Input coords=({cx}, {cy}), Target=({target_w}x{target_h})")
        # --- ADDED: Safety checks ---
        if not self.current_image:
            print("ERROR simulate_process: No current image loaded.")
            return None
        # REMOVED tk_image checks as they are not needed here anymore

        # --- Remove Redundant Coordinate conversion section ---
        # scale_x = self.current_image.width / tk_width # REMOVED
        # scale_y = self.current_image.height / tk_height # REMOVED
        # img_left = self.image_x - (tk_width // 2) # REMOVED
        # img_top = self.image_y - (tk_height // 2) # REMOVED
        # orig_x = int((cx - img_left) * scale_x) # REMOVED
        # orig_y = int((cy - img_top) * scale_y) # REMOVED
        # --- END REMOVE ---

        # --- Clamp the *input* coordinates (cx, cy) directly to image bounds ---
        print(f"DEBUG simulate_process: Before clamp: Input=({cx}, {cy}), ImageDims=({self.current_image.width}x{self.current_image.height})") # ADJUSTED PRINT
        orig_x = max(0, min(cx, self.current_image.width - 1))  # Clamp cx
        orig_y = max(0, min(cy, self.current_image.height - 1))  # Clamp cy
        print(f"DEBUG simulate_process: Clamped Orig=({orig_x}, {orig_y})")
        # --- End Clamping ---

        # Create new image at target size
        try: # --- ADDED: Try block for image creation ---
            # Ensure the canvas background is opaque for simulation
            r, g, b, _ = self.bg_color
            opaque_canvas_color = (r, g, b, 255)
            result = Image.new("RGBA", (target_w, target_h), opaque_canvas_color)

            # Calculate offsets using the *clamped original* coordinates (orig_x, orig_y)
            offset_x = target_w // 2 - orig_x # Use clamped original coords
            offset_y = target_h // 2 - orig_y # Use clamped original coords
            print(f"DEBUG simulate_process: Orig=({orig_x}, {orig_y}), Offset=({offset_x}, {offset_y})")

            # Calculate crop coordinates
            from_x = max(0, -offset_x)
            from_y = max(0, -offset_y)
            to_x = min(self.current_image.width, target_w - offset_x)
            to_y = min(self.current_image.height, target_h - offset_y)
            print(f"DEBUG simulate_process: Crop box=({from_x}, {from_y}) to ({to_x}, {to_y})")

            if from_x < to_x and from_y < to_y:
                cropped = self.current_image.crop((from_x, from_y, to_x, to_y))
                paste_x = max(0, offset_x)
                paste_y = max(0, offset_y)
                
                # Paste the 'cropped' image (which is RGBA) onto the 'result' image (opaque background).
                if cropped.mode == 'RGBA':
                    # If the cropped image has an alpha channel, use its alpha band as the mask.
                    result.paste(cropped, (paste_x, paste_y), mask=cropped.split()[3])
                elif cropped.mode == 'RGB':
                    # If cropped is RGB (no alpha), paste it directly.
                    result.paste(cropped, (paste_x, paste_y))
                else:
                    # Handle other modes or raise an error if necessary
                    self.logger.warning(f"simulate_process_image: Cropped image has unexpected mode {cropped.mode}. Pasting without mask.")
                    result.paste(cropped, (paste_x, paste_y))
            else:
                print(f"DEBUG simulate_process: Invalid crop coordinates: ({from_x}, {from_y}) to ({to_x}, {to_y})")
            return result # <<< ADDED THIS LINE TO RETURN THE PROCESSED IMAGE ON SUCCESS >>>
        except Exception as e: # --- ADDED: Catch errors during simulation ---
            error_message = f"ERROR simulate_process: Failed during image processing: {str(e)}"
            detailed_traceback = traceback.format_exc()
            
            # Force logging and output of the traceback
            print("--- SIMULATE_PROCESS_IMAGE ERROR ---") # For stdout visibility
            print(error_message)
            print(detailed_traceback)
            print("--- END SIMULATE_PROCESS_IMAGE ERROR ---")

            if hasattr(self, 'logger') and self.logger:
                self.logger.error(error_message) # Log simple error
                self.logger.error(f"TRACEBACK: {detailed_traceback}") # Log full traceback

            # --- ADDED: Show error in a messagebox ---
            try:
                from tkinter import messagebox # Ensure messagebox is available
                messagebox.showerror(
                    "Crop Preview Simulation Error",
                    f"An error occurred in simulate_process_image:\\n{error_message}\\n\\nTRACEBACK:\\n{detailed_traceback}"
                )
            except Exception as mb_e:
                print(f"CRITICAL_ERROR: Failed to show messagebox in simulate_process_image: {mb_e}")
                if hasattr(self, 'logger') and self.logger:
                    self.logger.critical(f"CRITICAL_ERROR: Failed to show messagebox in simulate_process_image: {mb_e}\\nOriginal error: {error_message}\\nOriginal traceback: {detailed_traceback}")
            # --- END ADDED ---
            return None # Return None on failure

    def rgb_to_hex(self, rgb_tuple):
        """Converts an RGB tuple to a hexadecimal color string."""
        # This is a class method, ensure it's the one used if self.rgb_to_hex is called.
        # The utils.rgb_to_hex is also available via import.
        try:
            # Use only the first three components (RGB) for hex conversion
            return f"#{rgb_tuple[0]:02x}{rgb_tuple[1]:02x}{rgb_tuple[2]:02x}"
        except (IndexError, TypeError) as e:
            self.logger.error(f"Invalid RGB tuple for rgb_to_hex: {rgb_tuple} - {e}")
            return "#000000" # Fallback to black
    
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
            self.update_bg_color_display()

        tk.Radiobutton(self.position_window, text="Top", variable=position_var, value="top", command=update_position).pack(anchor="w")
        tk.Radiobutton(self.position_window, text="Bottom", variable=position_var, value="bottom", command=update_position).pack(anchor="w")
        
        tk.Button(self.position_window, text="OK", command=self.position_window.destroy).pack(pady=10)

    def show_statistics(self):
        # Create a new window for statistics
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Application Statistics")
        stats_window.geometry("650x780") # Changed dimensions
        stats_window.resizable(True, True)

        # Create main frame with padding
        main_frame = ttk.Frame(stats_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Create a single canvas and scrollbar ---
        stats_canvas = tk.Canvas(main_frame)
        stats_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=stats_canvas.yview)
        scrollable_content_frame = ttk.Frame(stats_canvas)

        # Configure columns of the scrollable_content_frame to expand
        scrollable_content_frame.columnconfigure(0, weight=1) # For labels like "Total Files Processed"
        scrollable_content_frame.columnconfigure(1, weight=1) # For values like "100"

        scrollable_content_frame_id = stats_canvas.create_window((0, 0), window=scrollable_content_frame, anchor="nw")

        def on_canvas_configure(event):
            canvas_width = event.width
            stats_canvas.itemconfig(scrollable_content_frame_id, width=canvas_width)
            # Update scrollregion after the content frame's width is set.
            # Using after_idle to ensure bbox calculation is accurate after width change.
            def update_bbox():
                if stats_canvas.winfo_exists(): # Check if canvas still exists
                    stats_canvas.configure(scrollregion=stats_canvas.bbox("all"))
            stats_canvas.after_idle(update_bbox)

        stats_canvas.bind("<Configure>", on_canvas_configure)

        # Original binding on scrollable_content_frame is removed as on_canvas_configure is more comprehensive.
        # scrollable_content_frame.bind(
        #     "<Configure>",
        #     lambda e: stats_canvas.configure(scrollregion=stats_canvas.bbox("all"))
        # )

        stats_scrollbar.pack(side="right", fill="y")
        stats_canvas.pack(side="left", fill="both", expand=True)
        # --- End single canvas setup ---

        # --- Helper function to recursively bind scroll events ---
        def bind_scroll_to_children(widget, canvas):
            widget.bind("<MouseWheel>", lambda e, c=canvas: self._on_mousewheel_scroll_stats(e, c))
            widget.bind("<Button-4>", lambda e, c=canvas: self._on_mousewheel_scroll_stats(e, c)) # For Linux
            widget.bind("<Button-5>", lambda e, c=canvas: self._on_mousewheel_scroll_stats(e, c)) # For Linux
            for child in widget.winfo_children():
                bind_scroll_to_children(child, canvas)
        # --- End Helper ---

        # Get formatted stats
        stats = self.stats_manager.get_formatted_stats()
        # <<< ADDED DEBUG PRINT: Show raw stats data >>>
        print(f"DEBUG show_statistics: Raw stats data: {stats}")
        # <<< END ADDED >>>

        try:
            # --- Populate the single scrollable_content_frame ---
            current_row = 0

            # Helper to add a section title
            def add_section_title(title, row):
                ttk.Label(scrollable_content_frame, text=title, font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(20 if row > 0 else 10, 5), padx=5)
                return row + 1

            # Helper to add a stat item
            def add_stat_item(label_text, value_text, row):
                ttk.Label(scrollable_content_frame, text=label_text + (":" if value_text else ""), font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=(20, 10))
                ttk.Label(scrollable_content_frame, text=value_text, font=("Arial", 10)).grid(row=row, column=1, sticky="w", padx=(0, 5))
                return row + 1

            # General Statistics
            current_row = add_section_title("General Statistics", current_row)
            general_stats_items = [
                ("Total Files Processed", str(stats["total_files"])),
                ("Total Time Spent", stats["total_time"]),
                ("Estimated Time Saved", stats["time_saved"]),
                ("Total Sessions", str(stats["session_count"])),
                ("Files This Session", str(stats["current_session_files"])),
                ("Largest Batch", str(stats.get("largest_batch", 0))),
                ("Longest Session", stats.get("longest_session", "N/A"))
            ]
            for label, value in general_stats_items:
                # <<< ADDED DEBUG PRINT: Confirm section loop runs >>>
                print(f"DEBUG show_statistics: Processing section: General Statistics")
                # <<< END ADDED >>>
                current_row = add_stat_item(label, value, current_row)

            # Recent Activity
            current_row = add_section_title("Recent Activity", current_row)
            recent_activity_items = [
                ("Last Access", stats["last_access"]),
                ("Last File Processed", stats.get("last_file", {}).get("name", "None")),
                ("Last File Time", stats.get("last_file", {}).get("time", "None"))
            ]
            for label, value in recent_activity_items:
                 print(f"DEBUG show_statistics: Processing section: Recent Activity")
                 current_row = add_stat_item(label, value, current_row)

            # Top File Types
            current_row = add_section_title("Top File Types", current_row)
            for ftype, count in stats.get("top_file_types", []):
                print(f"DEBUG show_statistics: Processing section: Top File Types")
                current_row = add_stat_item(f"{ftype.upper()}", f"{count} file(s)", current_row)

            # Pixels Processed
            current_row = add_section_title("Pixels Processed", current_row)
            current_row = add_stat_item("Total Pixels", f"{stats.get('total_pixels', 0):,}", current_row)
            for res, count in stats.get("pixels_by_resolution", {}).items():
                print(f"DEBUG show_statistics: Processing section: Pixels Processed")
                current_row = add_stat_item(f"{res}", f"{count:,} px", current_row)
            
            # Top 5 Background Colors
            current_row = add_section_title("Top 5 Background Colors", current_row)
            color_display_frame = ttk.Frame(scrollable_content_frame)
            color_display_frame.grid(row=current_row, column=0, columnspan=2, sticky="w", padx=20)
            current_row +=1 # Increment row for the frame itself
            for i, (color, count) in enumerate(stats["top_colors"]):
                color_box = tk.Label(color_display_frame, text=f"{color} ({count})", width=20, bg=color)
                if self.is_dark_color(color):
                    color_box.config(fg="white")
                color_box.pack(pady=2, anchor="w") # anchor west to align with labels

            # Top 5 Resolutions
            current_row = add_section_title("Top 5 Resolutions", current_row)
            for resolution, count in stats["top_resolutions"]:
                text = f"{resolution} ({count} times)"
                current_row = add_stat_item(text, "", current_row) # No separate value column

            # Top 5 Folders
            current_row = add_section_title(f"Top 5 Folders (Total: {len(stats.get('folders_extracted', []))})", current_row)
            for folder in stats.get("folders_extracted", [])[:5]:
                # <<< ADDED DEBUG PRINT: Confirm folder loop runs >>>
                print(f"DEBUG show_statistics: Adding folder: {folder}")
                # <<< END ADDED >>>
                # Display each folder as a single item spanning two columns or in the first column
                # Changed sticky to "ew" to allow the label to expand horizontally
                folder_label = ttk.Label(scrollable_content_frame, text=folder, font=("Arial", 10), wraplength=main_frame.winfo_width() - 50) # Adjust wraplength
                folder_label.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=20, pady=2)
                current_row += 1
            
            # Add OK button at the bottom of the main_frame, not the scrollable one
            button_frame = ttk.Frame(main_frame) # Parent is main_frame
            button_frame.pack(fill=tk.X, pady=10, side=tk.BOTTOM) # Pack at the very bottom
            ttk.Button(button_frame, text="OK :)", command=stats_window.destroy).pack(side=tk.RIGHT, padx=10)

            # --- Bind scroll events AFTER all content is added to scrollable_content_frame ---
            bind_scroll_to_children(scrollable_content_frame, stats_canvas)
            # --- End Bind scroll events ---

        except Exception as e:
            self.logger.error(f"Error populating statistics window: {str(e)}")
            self.logger.error(traceback.format_exc())
            messagebox.showerror("Stats Error", f"Could not display statistics: {str(e)}")
            stats_window.destroy()
        
        # Force update of the layout
        stats_window.update_idletasks()
        
        # <<< ADDED DEBUG PRINT: Check scroll regions >>>
        try:
            # Ensure canvas has had a chance to update its contents' bounding box
            stats_canvas.update_idletasks()
            bbox = stats_canvas.bbox("all")
            print(f"DEBUG show_statistics: Scrollregion bbox: {bbox}")
            stats_canvas.config(scrollregion=bbox) # Explicitly set scrollregion
        except Exception as bbox_e:
            print(f"DEBUG show_statistics: Error getting bbox or configuring scrollregion: {bbox_e}")
        # <<< END ADDED >>>

        # Bring the window to front
        stats_window.lift()
        stats_window.focus_force()

        # <<< ADDED DEBUG PRINT: Check scroll regions >>>
        try:
            # Ensure the scrollable_content_frame itself has computed its size
            scrollable_content_frame.update_idletasks()
            # Ensure the canvas has also processed pending tasks
            stats_canvas.update_idletasks()

            # Set the scrollregion of the canvas to the actual required size of the content frame
            content_width = scrollable_content_frame.winfo_reqwidth()
            content_height = scrollable_content_frame.winfo_reqheight()
            stats_canvas.config(scrollregion=(0, 0, content_width, content_height))
            print(f"DEBUG show_statistics: Set scrollregion to (0,0, {content_width}, {content_height})")

        except Exception as e_scroll:
            print(f"DEBUG show_statistics: Error configuring scrollregion with winfo_reqwidth/height: {e_scroll}")
            # Fallback to bbox if winfo_reqwidth/height fails
            try:
                bbox = stats_canvas.bbox("all")
                if bbox:
                    stats_canvas.config(scrollregion=bbox)
                    print(f"DEBUG show_statistics: Fallback scrollregion to bbox: {bbox}")
                else:
                    print(f"DEBUG show_statistics: Fallback bbox was None or empty.")
            except Exception as e_bbox_fallback:
                print(f"DEBUG show_statistics: Error in fallback scrollregion config (bbox): {e_bbox_fallback}")
        # <<< END ADDED >>>

        # Bring the window to front
        stats_window.lift()

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

    def _on_mousewheel_scroll_stats(self, event, canvas_widget):
        """Handle mousewheel scrolling for a given canvas."""
        if event.num == 5 or event.delta < 0:
            canvas_widget.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            canvas_widget.yview_scroll(-1, "units")

    def _on_mousewheel_scroll_manual_content(self, event, canvas_widget):
        """Handle mousewheel scrolling specifically for the manual's content canvas."""
        # Determine scroll direction
        if event.num == 5 or event.delta < 0: # Scroll down
            canvas_widget.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0: # Scroll up
            canvas_widget.yview_scroll(-1, "units")

    def _bind_mousewheel_for_manual_scroll(self, widget, canvas_to_scroll):
        """Recursively bind mousewheel events on a widget and its children to scroll the manual's content canvas."""
        widget.bind("<MouseWheel>", lambda e, c=canvas_to_scroll: self._on_mousewheel_scroll_manual_content(e, c))
        widget.bind("<Button-4>", lambda e, c=canvas_to_scroll: self._on_mousewheel_scroll_manual_content(e, c)) # For Linux scroll up
        widget.bind("<Button-5>", lambda e, c=canvas_to_scroll: self._on_mousewheel_scroll_manual_content(e, c)) # For Linux scroll down
        for child in widget.winfo_children():
            self._bind_mousewheel_for_manual_scroll(child, canvas_to_scroll)

    def quit_app(self):
        self.stats_manager.end_session()
        self.root.quit()

    def show_manual(self):
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Manual")
        
        main_layout_frame = ttk.Frame(manual_window, padding="5")
        main_layout_frame.pack(fill=tk.BOTH, expand=True)

        button_panel_container = ttk.Frame(main_layout_frame, width=220) # Adjusted width
        button_panel_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), pady=5)
        button_panel_container.pack_propagate(False)

        btn_canvas = tk.Canvas(button_panel_container, highlightthickness=0)
        btn_scrollbar = ttk.Scrollbar(button_panel_container, orient="vertical", command=btn_canvas.yview)
        scrollable_buttons_frame = ttk.Frame(btn_canvas)

        scrollable_buttons_frame.bind(
            "<Configure>",
            lambda e: btn_canvas.configure(scrollregion=btn_canvas.bbox("all"))
        )
        btn_canvas.create_window((0, 0), window=scrollable_buttons_frame, anchor="nw")
        btn_canvas.configure(yscrollcommand=btn_scrollbar.set)

        btn_scrollbar.pack(side="right", fill="y")
        btn_canvas.pack(side="left", fill="both", expand=True)
        
        content_area_container = ttk.Frame(main_layout_frame, padding="5")
        content_area_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        content_canvas = tk.Canvas(content_area_container, highlightthickness=0)
        content_scrollbar = ttk.Scrollbar(content_area_container, orient="vertical", command=content_canvas.yview)
        self.scrollable_content_display_frame = ttk.Frame(content_canvas) 
        
        self.scrollable_content_display_frame.bind(
            "<Configure>",
            lambda e: content_canvas.configure(scrollregion=content_canvas.bbox("all"))
        )
        content_canvas.create_window((0, 0), window=self.scrollable_content_display_frame, anchor="nw")
        content_canvas.configure(yscrollcommand=content_scrollbar.set)
        
        content_scrollbar.pack(side="right", fill="y")
        content_canvas.pack(side="left", fill="both", expand=True)
        
        md_content_full = None
        error_message_manual = None

        try:
            if self.manual_content_data:
                md_content_full = self.manual_content_data
                self.logger.info("Using pre-loaded manual content for display.")
            else:
                self.logger.info("Pre-loaded manual content not found. Attempting to load manual.md.")
                
                path_to_try = None
                # Determine the base path for loading resources
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    # Application is frozen (packaged by PyInstaller)
                    # Files added with --add-data (e.g., "manual.md:.") are in sys._MEIPASS
                    base_dir = sys._MEIPASS
                    self.logger.info(f"Running packaged. Trying manual.md from _MEIPASS: {base_dir}")
                else:
                    # Application is not frozen (running from script)
                    # __file__ is the path to the current script (resizer_app.pyw)
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    self.logger.info(f"Running from script. Trying manual.md from script directory: {base_dir}")
                
                path_to_try = os.path.join(base_dir, "manual.md")
                
                if os.path.exists(path_to_try):
                    with open(path_to_try, "r", encoding="utf-8") as f:
                        md_content_full = f.read()
                    self.logger.info(f"Successfully loaded manual.md from: {path_to_try}")
                else:
                    # If packaged and not found in _MEIPASS, try next to the .exe as a fallback.
                    if getattr(sys, 'frozen', False):
                        exe_dir = os.path.dirname(sys.executable)
                        fallback_path = os.path.join(exe_dir, "manual.md")
                        self.logger.info(f"Manual not found at '{path_to_try}'. Trying fallback next to executable: {fallback_path}")
                        if os.path.exists(fallback_path):
                            with open(fallback_path, "r", encoding="utf-8") as f:
                                md_content_full = f.read()
                            self.logger.info(f"Successfully loaded manual.md from beside executable: {fallback_path}")
                        else:
                            error_message_manual = f"Manual file (manual.md) not found. Primary attempt: '{path_to_try}'. Fallback attempt: '{fallback_path}'."
                            self.logger.warning(error_message_manual)
                    else:
                        # Not packaged, and not found next to script
                        error_message_manual = f"Manual file (manual.md) not found at: {path_to_try}"
                        self.logger.warning(error_message_manual)
            
            if md_content_full:
                sections = []
                current_section_title = None
                current_section_lines = []

                # Normalize newlines before splitting for section identification
                normalized_content = md_content_full.replace('\\n', '\n').replace('\r\n', '\n').replace('\r', '\n')
                lines_to_parse_for_sections = normalized_content.split('\n')
                for line in lines_to_parse_for_sections:
                    if line.startswith("# ") or line.startswith("## "):
                        if current_section_title:
                            # Join the collected lines for the current section with real newlines
                            sections.append((current_section_title, "\n".join(current_section_lines)))
                        current_section_title = line[2:].strip() if line.startswith("# ") else line[3:].strip()
                        current_section_lines = []
                    else:
                        current_section_lines.append(line)
                if current_section_title:
                    sections.append((current_section_title, "\n".join(current_section_lines)))
                if not sections and md_content_full.strip():
                    # If no headers, treat the whole thing as one section
                    sections.append(("Manual", normalized_content))

                for topic_title, topic_md_content_data in sections:
                    btn = ttk.Button(
                        scrollable_buttons_frame,
                        text=topic_title,
                        command=lambda t=topic_title, tc=topic_md_content_data:
                            self.update_manual_content(
                                frame_to_update=self.scrollable_content_display_frame, 
                                topic=t, 
                                content=tc, 
                                canvas_for_sizing=content_canvas
                            )
                    )
                    btn.pack(fill="x", padx=5, pady=3)
                
                if sections:
                    manual_window.update_idletasks()
                    self.update_manual_content(
                        frame_to_update=self.scrollable_content_display_frame, 
                        topic=sections[0][0], 
                        content=sections[0][1], 
                        canvas_for_sizing=content_canvas
                    )
                    self._bind_mousewheel_for_manual_scroll(self.scrollable_content_display_frame, content_canvas)
                elif not error_message_manual: # Content was there but parsing resulted in no sections (e.g. empty file)
                    error_message_manual = "Manual content is empty or could not be parsed into sections."
                    self.logger.warning(error_message_manual)

            if error_message_manual: # If any error occurred or content was missing
                 ttk.Label(self.scrollable_content_display_frame, text=error_message_manual, foreground="red", wraplength=300).pack(padx=10, pady=10)

            # Window sizing and positioning (moved out of try block to always execute if window is created)
            screen_width = manual_window.winfo_screenwidth()
            screen_height = manual_window.winfo_screenheight()
            window_width = int(screen_width * 0.60)
            window_height = int(screen_height * 0.60)
            manual_window.geometry(f"{window_width}x{window_height}")
            manual_window.minsize(int(screen_width * 0.40), int(screen_height * 0.40))
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            manual_window.geometry(f"+{x}+{y}")
            manual_window.lift()
            manual_window.focus_force()

        except Exception as e:
            # General error handling for unexpected issues during manual display setup
            error_target = self.scrollable_content_display_frame if hasattr(self, 'scrollable_content_display_frame') and self.scrollable_content_display_frame.winfo_exists() else manual_window
            ttk.Label(error_target, text=f"Error loading manual: {str(e)}", foreground="red").pack(padx=10, pady=10)
            log_msg = f"Error in show_manual: {e}\\n{traceback.format_exc()}"
            if hasattr(self, 'logger') and self.logger:
                 self.logger.error(log_msg)
            else:
                 print(log_msg)

    def update_manual_content(self, frame_to_update, topic, content, canvas_for_sizing):
        for widget in frame_to_update.winfo_children():
            widget.destroy()

        canvas_for_sizing.update_idletasks()
        available_width = canvas_for_sizing.winfo_width()
        effective_wraplength = int(available_width * 0.92) # Give some padding
        effective_wraplength = max(200, effective_wraplength)

        title_label = ttk.Label(frame_to_update, text=topic, font=("Arial", 16, "bold"), wraplength=effective_wraplength - 20)
        title_label.pack(pady=(5,15), fill='x', padx=10)

        content_elements_host_frame = ttk.Frame(frame_to_update)
        content_elements_host_frame.pack(padx=10, pady=5, fill="both", expand=True)

        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        default_font = ("Arial", 10)

        def _open_url_closure(url_to_open):
            def _open(event):
                webbrowser.open_new(url_to_open)
            return _open

        paragraph_buffer = []
        code_block_active = False
        code_buffer = []
        current_list_frame = None

        def flush_paragraph(target_parent):
            nonlocal paragraph_buffer
            if paragraph_buffer:
                text = "\n".join(p.strip() for p in paragraph_buffer if p.strip())
                if text:
                    para_line_frame = ttk.Frame(target_parent)
                    para_line_frame.pack(fill='x', anchor='w', pady=(0, 5))
                    
                    last_idx = 0
                    for match in link_pattern.finditer(text):
                        s, e = match.span()
                        if s > last_idx:
                            self._manual_process_formatted_text(para_line_frame, text[last_idx:s], default_font, effective_wraplength)
                        link_text, url = match.groups()
                        link_font = list(default_font) + ["underline"]
                        link_label = ttk.Label(para_line_frame, text=link_text, font=tuple(link_font), foreground="blue", cursor="hand2")
                        link_label.pack(side=tk.LEFT, pady=0)
                        link_label.bind("<Button-1>", _open_url_closure(url))
                        last_idx = e
                    if last_idx < len(text):
                        self._manual_process_formatted_text(para_line_frame, text[last_idx:], default_font, effective_wraplength)
                paragraph_buffer = []
            return True # Indicates a flush happened or was not needed

        for raw_line in content.split("\n"):
            line = raw_line.rstrip()

            if line.startswith("```"):
                flush_paragraph(content_elements_host_frame)
                current_list_frame = None
                if code_block_active:
                    code_block_active = False
                    if code_buffer:
                        code_frame = ttk.Frame(content_elements_host_frame, relief="solid", borderwidth=1)
                        code_frame.pack(fill="x", pady=5, padx=5)
                        code_text = "\n".join(code_buffer)
                        # For code block, apply wraplength to the label itself
                        ttk.Label(code_frame, text=code_text, font=("Courier", 10), background="#f0f0f0", wraplength=effective_wraplength-20, justify=tk.LEFT).pack(padx=5,pady=5,fill='x')
                        code_buffer = []
                else:
                    code_block_active = True
                continue

            if code_block_active:
                code_buffer.append(raw_line) # Preserve original line for code
                continue
            
            # Headings (H1, H2, H3)
            if line.startswith("#"):
                flush_paragraph(content_elements_host_frame)
                current_list_frame = None
                level = line.count("#")
                text = line.lstrip("# ").strip()
                font_size = 14 if level == 1 else (12 if level == 2 else 11)
                header_font_style = ("Arial", font_size, "bold")
                
                header_line_frame = ttk.Frame(content_elements_host_frame)
                header_line_frame.pack(fill='x', anchor='w', pady=(10 if level==1 else 7, 3))
                # Headers can also contain links or other formatting
                self._manual_process_formatted_text(header_line_frame, text, header_font_style, effective_wraplength)
                continue

            # List Items
            if line.startswith("- "): # Only hyphens for lists
                flush_paragraph(content_elements_host_frame)
                if current_list_frame is None or not current_list_frame.winfo_exists():
                    current_list_frame = ttk.Frame(content_elements_host_frame)
                    current_list_frame.pack(fill='x', anchor='w', padx=(20,0), pady=2)
                
                item_line_frame = ttk.Frame(current_list_frame)
                item_line_frame.pack(fill='x', anchor='w')
                ttk.Label(item_line_frame, text="•", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0,5), pady=0)
                
                list_text = line[2:].strip()
                # Process list text for links and other formatting
                last_idx = 0
                for match in link_pattern.finditer(list_text):
                    s, e = match.span()
                    if s > last_idx:
                        self._manual_process_formatted_text(item_line_frame, list_text[last_idx:s], default_font, effective_wraplength)
                    link_t, url = match.groups()
                    link_f = list(default_font) + ["underline"]
                    li_link_lbl = ttk.Label(item_line_frame, text=link_t, font=tuple(link_f), foreground="blue", cursor="hand2")
                    li_link_lbl.pack(side=tk.LEFT, pady=0)
                    li_link_lbl.bind("<Button-1>", _open_url_closure(url))
                    last_idx = e
                if last_idx < len(list_text):
                    self._manual_process_formatted_text(item_line_frame, list_text[last_idx:], default_font, effective_wraplength)
                continue
            
            # Regular paragraph lines or end of list
            if line.strip():
                current_list_frame = None # A non-empty, non-list, non-header line breaks list context
                paragraph_buffer.append(line)
            else: # Empty line implies paragraph break
                flush_paragraph(content_elements_host_frame)
                current_list_frame = None
        
        flush_paragraph(content_elements_host_frame) # Flush any remaining paragraph

        frame_to_update.update_idletasks()
        canvas_for_sizing.update_idletasks()
        canvas_for_sizing.config(scrollregion=canvas_for_sizing.bbox("all"))
        # Re-bind scrolling for the newly loaded content
        self._bind_mousewheel_for_manual_scroll(frame_to_update, canvas_for_sizing)

    def _manual_process_formatted_text(self, parent_line_frame, text_segment, base_font_tuple, effective_wraplength):
        parts = text_segment.split('**')
        for i, part in enumerate(parts):
            if not part and len(parts) > 1: # Handle empty string from adjacent ** or start/end **
                continue
            if i % 2 == 0: # Regular text or text between bold segments
                self._manual_process_italic_text(parent_line_frame, part, base_font_tuple, effective_wraplength)
            else: # Bold text
                styled_font = list(base_font_tuple)
                # Append or prepend 'bold' to existing style
                style_index = 2 if len(styled_font) > 2 else -1
                if style_index != -1 and isinstance(styled_font[style_index], str) and styled_font[style_index]:
                    if "bold" not in styled_font[style_index].lower():
                        styled_font[style_index] += " bold"
                elif style_index == -1 : # Add style if font tuple was (family, size)
                     styled_font.append("bold")
                else: # If style slot was empty or not string
                    styled_font[style_index if style_index != -1 else len(styled_font)-1] = "bold"
                
                ttk.Label(parent_line_frame, text=part, font=tuple(styled_font), wraplength=effective_wraplength).pack(side=tk.LEFT, pady=0)

    def _manual_process_italic_text(self, parent_line_frame, text_segment, base_font_tuple, effective_wraplength):
        # Avoid splitting if the segment starts with list marker like '* '
        if text_segment.startswith("* ") and len(text_segment) > 2 : # Common for list items, not italics
             ttk.Label(parent_line_frame, text=text_segment, font=base_font_tuple, wraplength=effective_wraplength).pack(side=tk.LEFT, pady=0)
             return

        parts = text_segment.split('*')
        for i, part in enumerate(parts):
            if not part and len(parts) > 1: # Handle empty string from adjacent * or start/end *
                continue
            if i % 2 == 0: # Regular text or text between italic segments
                if part: # Only pack if there is text
                    ttk.Label(parent_line_frame, text=part, font=base_font_tuple, wraplength=effective_wraplength).pack(side=tk.LEFT, pady=0)
            else: # Italic text
                styled_font = list(base_font_tuple)
                style_index = 2 if len(styled_font) > 2 else -1
                if style_index != -1 and isinstance(styled_font[style_index], str) and styled_font[style_index]:
                    if "italic" not in styled_font[style_index].lower():
                         styled_font[style_index] += " italic"
                elif style_index == -1:
                    styled_font.append("italic")
                else:
                    styled_font[style_index if style_index != -1 else len(styled_font)-1] = "italic"
                
                ttk.Label(parent_line_frame, text=part, font=tuple(styled_font), wraplength=effective_wraplength).pack(side=tk.LEFT, pady=0)

    def get_contrasting_text_color(self, bg_color):
        # Convert RGB to relative luminance (WCAG 2.0 formula)
        r, g, b = bg_color[:3] # Use only RGB components if RGBA
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

    def on_mouse_wheel(self, event, delta=None):
        """Handle mouse wheel zooming."""
        if self.eyedropper_active:
            return
            
        # Get the current mouse position relative to the canvas
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Get the delta from the event or use the provided one
        if delta is None:
            delta = event.delta
        
        # Calculate zoom factor
        if delta > 0:
            # Zoom in
            new_zoom = min(self.zoom_level * self.zoom_factor, self.max_zoom)
        else:
            # Zoom out
            new_zoom = max(self.zoom_level / self.zoom_factor, self.min_zoom)
        
        # Calculate the mouse position relative to the image center
        offset_x = x - self.image_x
        offset_y = y - self.image_y
        
        # Update zoom level
        old_zoom = self.zoom_level
        self.zoom_level = new_zoom
        
        # Calculate new scroll position to keep the mouse position fixed
        self.scroll_x = offset_x - (offset_x * new_zoom / old_zoom)
        self.scroll_y = offset_y - (offset_y * new_zoom / old_zoom)
        
        # Redraw the image
        self.show_image()

    def start_pan(self, event):
        """Start panning when middle mouse button is pressed."""
        if self.eyedropper_active:
            return
        self.is_panning = True
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def stop_pan(self, event):
        """Stop panning when middle mouse button is released."""
        self.is_panning = False

    def on_mouse_wheel_hold(self, event):
        """Handle panning when middle mouse button is held."""
        if not self.is_panning or self.eyedropper_active:
            return
            
        # Calculate the movement
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        
        # Update scroll position
        self.scroll_x += dx
        self.scroll_y += dy
        
        # Update last mouse position
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        
        # Redraw the image
        self.show_image()

    def reset_zoom(self, event=None):
        """Reset zoom to 100%."""
        self.zoom_level = 1.0
        self.scroll_x = 0
        self.scroll_y = 0
        self.show_image()

    def zoom_in(self, event=None):
        """Zoom in by 10%."""
        if self.eyedropper_active:
            return
            
        # Get the current mouse position relative to the canvas
        x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        
        # Calculate new zoom level
        new_zoom = min(self.zoom_level * self.zoom_factor, self.max_zoom)
        
        # Calculate the mouse position relative to the image center
        offset_x = x - self.image_x
        offset_y = y - self.image_y
        
        # Update zoom level
        self.zoom_level = new_zoom
        
        # Calculate new scroll position to keep the mouse position fixed
        self.scroll_x = offset_x - (offset_x * new_zoom / self.zoom_level)
        self.scroll_y = offset_y - (offset_y * new_zoom / self.zoom_level)
        
        # Redraw the image
        self.show_image()

    def zoom_out(self, event=None):
        """Zoom out by 10%."""
        if self.eyedropper_active:
            return
            
        # Get the current mouse position relative to the canvas
        x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        
        # Calculate new zoom level
        new_zoom = max(self.zoom_level / self.zoom_factor, self.min_zoom)
        
        # Calculate the mouse position relative to the image center
        offset_x = x - self.image_x
        offset_y = y - self.image_y
        
        # Update zoom level
        self.zoom_level = new_zoom
        
        # Calculate new scroll position to keep the mouse position fixed
        self.scroll_x = offset_x - (offset_x * new_zoom / self.zoom_level)
        self.scroll_y = offset_y - (offset_y * new_zoom / self.zoom_level)
        
        # Redraw the image
        self.show_image()

    def reset_bg_color(self, event=None):
        """Reset background color to magenta (#ff00ff)."""
        self.bg_color = (255, 0, 255, 255)  # Magenta in RGBA
        self.update_bg_color_label()
        if self.preview_mode_var.get() == "Show Last Output" and self.last_output_path:
            self.update_last_output_preview()

    def on_horizontal_scroll(self, event, delta=None):
        """Handle horizontal scrolling with Ctrl+scrollwheel."""
        if self.eyedropper_active:
            return
        """Reset background color to magenta (#ff00ff)."""
        self.bg_color = (255, 0, 255, 255)  # Magenta in RGBf
        if delta is None:
            delta = event.delta
            
        # Calculate scroll amount (adjust this value to change scroll speed)
        scroll_amount = delta / 120 * 20  # 20 pixels per scroll step
        
        # Update horizontal scroll position
        self.scroll_x += scroll_amount
        
        # Redraw the image
        self.show_image()

    def on_vertical_scroll(self, event, delta=None):
        """Handle vertical scrolling with Ctrl+Shift+scrollwheel."""
        if self.eyedropper_active:
            return
            
        # Get the delta from the event or use the provided one
        if delta is None:
            delta = event.delta
            
        # Calculate scroll amount (adjust this value to change scroll speed)
        scroll_amount = delta / 120 * 20  # 20 pixels per scroll step
        
        # Update vertical scroll position
        self.scroll_y += scroll_amount
        
        # Redraw the image
        self.show_image()

    def custom_crosshair_dialog(self):
        """Show dialog for custom crosshair size."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Custom Crosshair Size")
        dialog.transient(self.root)  # Make dialog modal
        dialog.grab_set()  # Grab focus
        
        # Center dialog on screen
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        # Create size input
        size_frame = tk.Frame(dialog, padx=10, pady=10)
        size_frame.pack(fill=tk.X)
        
        tk.Label(size_frame, text="Size (pixels):").pack(side=tk.LEFT)
        size_var = tk.StringVar(value=str(self.custom_crosshair_size))
        size_entry = tk.Entry(size_frame, textvariable=size_var, width=5)
        size_entry.pack(side=tk.LEFT, padx=5)
        
        # Create buttons
        button_frame = tk.Frame(dialog, padx=10, pady=5)
        button_frame.pack(fill=tk.X)
        
        def apply_size():
            try:
                size = int(size_var.get())
                if size < 1:
                    raise ValueError("Size must be at least 1")
                self.custom_crosshair_size = size
                self.crosshair_mode_var.set("custom")
                self.update_crosshair()
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))
        
        tk.Button(button_frame, text="OK", command=apply_size).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)
        
        # Focus the entry and select its contents
        size_entry.focus_set()
        size_entry.select_range(0, tk.END)

    def crosshair_color_dialog(self):
        """Show dialog for crosshair color options."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Crosshair Color")
        dialog.transient(self.root)  # Make dialog modal
        dialog.grab_set()  # Grab focus
        
        # Center dialog on screen
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        # Create main frame
        main_frame = tk.Frame(dialog, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create preview frame
        preview_frame = tk.Frame(main_frame)
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create preview canvas
        preview_canvas = tk.Canvas(preview_frame, width=100, height=100, bg="gray")
        preview_canvas.pack(side=tk.LEFT, padx=(0, 10))
        
        # Create preview label
        preview_label = tk.Label(preview_frame, text="Preview", font=("Arial", 10))
        preview_label.pack(side=tk.LEFT)
        
        # Create negative color option
        negative_frame = tk.Frame(main_frame)
        negative_frame.pack(fill=tk.X, pady=(0, 10))
        
        negative_var = tk.BooleanVar(value=self.crosshair_color_mode.get() == "negative")
        
        def update_preview():
            if negative_var.get():
                # Create a sample image for negative preview
                sample_img = Image.new("RGB", (100, 100), (128, 128, 128))
                sample_pixels = sample_img.load()
                for y in range(100):
                    for x in range(100):
                        if (x - 50) ** 2 + (y - 50) ** 2 < 400:  # Circle
                            sample_pixels[x, y] = (64, 64, 64)
                # Convert to negative
                neg_img = Image.eval(sample_img, lambda x: 255 - x)
                preview_img = ImageTk.PhotoImage(neg_img)
            else:
                # Create a sample image with the selected color
                sample_img = Image.new("RGB", (100, 100), (128, 128, 128))
                sample_pixels = sample_img.load()
                for y in range(100):
                    for x in range(100):
                        if (x - 50) ** 2 + (y - 50) ** 2 < 400:  # Circle
                            # Convert hex to RGB
                            color = self.crosshair_color.lstrip('#')
                            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                            sample_pixels[x, y] = rgb
                preview_img = ImageTk.PhotoImage(sample_img)
            
            preview_canvas.create_image(50, 50, image=preview_img)
            preview_canvas.image = preview_img  # Keep reference
        
        def toggle_negative():
            if negative_var.get():
                self.crosshair_color_mode.set("negative")
                color_frame.pack_forget()
            else:
                self.crosshair_color_mode.set("custom")
                color_frame.pack(fill=tk.X, pady=(10, 0))
            update_preview()
            self.update_crosshair()
        
        tk.Checkbutton(
            negative_frame, 
            text="Negative (Invert Pixel Colors)", 
            variable=negative_var,
            command=toggle_negative
        ).pack(side=tk.LEFT)
        
        # Create color selection frame
        color_frame = tk.Frame(main_frame)
        if not negative_var.get():
            color_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create color buttons in a grid
        color_buttons = []
        for i, (name, color) in enumerate(self.pixel_colors.items()):
            row = i // 4
            col = i % 4
            
            def create_color_button(name, color):
                btn = tk.Button(
                    color_frame,
                    text=name,
                    bg=color,
                    fg="white" if self.is_dark_color(color) else "black",
                    width=10,
                    command=lambda c=color: self.set_crosshair_color(c, update_preview)
                )
                return btn
            
            btn = create_color_button(name, color)
            btn.grid(row=row, column=col, padx=5, pady=5)
            color_buttons.append(btn)
        
        # Create buttons
        button_frame = tk.Frame(dialog, padx=10, pady=5)
        button_frame.pack(fill=tk.X)
        
        tk.Button(button_frame, text="OK", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)
        
        # Show initial preview
        update_preview()

    def set_crosshair_color(self, color, update_preview=None):
        """Set the crosshair color and update the display."""
        self.crosshair_color = color
        self.crosshair_use_negative.set(False) # Turn off negative mode when a specific color is chosen
        if hasattr(self, 'color_preview_label') and self.color_preview_label: # Update preview if it exists
            self.color_preview_label.config(bg=self.crosshair_color, state="normal")
        self.update_crosshair() # Update the actual crosshair

    def grid_color_dialog(self):
        """Show dialog for grid color options."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Grid Color")
        dialog.transient(self.root)  # Make dialog modal
        dialog.grab_set()  # Grab focus
        
        # Center dialog on screen
        dialog.update_idletasks()
        # <<< Use reqwidth/reqheight for centering before explicit sizing >>>
        width = dialog.winfo_reqwidth()
        height = dialog.winfo_reqheight()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        # Create main frame
        main_frame = tk.Frame(dialog, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame for preset color buttons
        preset_color_frame = ttk.LabelFrame(main_frame, text="Preset Colors")
        preset_color_frame.pack(fill=tk.X, pady=(0, 10))

        color_buttons_frame = ttk.Frame(preset_color_frame) # Inner frame for grid layout
        color_buttons_frame.pack(pady=5)

        self.grid_preset_buttons = [] # Store preset buttons to toggle their state
        for i, (name, color_val) in enumerate(self.grid_colors.items()):
            row = i // 4
            col = i % 4
            
            btn = tk.Button(
                color_buttons_frame,
                text=name,
                bg=color_val,
                fg="white" if self.is_dark_color(color_val) else "black",
                width=8, # Adjusted width
                command=lambda c=color_val: self.set_grid_color_from_preset(c, dialog)
            )
            btn.grid(row=row, column=col, padx=3, pady=3) # Adjusted padding
            self.grid_preset_buttons.append(btn)

        # Custom Color Picker Section
        custom_color_controls_frame = ttk.LabelFrame(main_frame, text="Custom Color")
        custom_color_controls_frame.pack(fill=tk.X, pady=(0, 10))

        self.custom_grid_color_button = tk.Button(
            custom_color_controls_frame,
            text="Pick Custom Color...",
            command=lambda: self.pick_grid_color_via_chooser(dialog),
            width=20 # Adjusted width
        )
        self.custom_grid_color_button.pack(pady=5)

        preview_custom_frame = ttk.Frame(custom_color_controls_frame)
        preview_custom_frame.pack(pady=(0,5))
        ttk.Label(preview_custom_frame, text="Current Custom:").pack(side=tk.LEFT, padx=(0,5))
        self.custom_grid_color_preview_label = tk.Label(
            preview_custom_frame,
            bg=self.grid_custom_color, 
            width=10,
            height=1,
            bd=1,
            relief="sunken"
        )
        self.custom_grid_color_preview_label.pack(side=tk.LEFT)
        
        # OK button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10,0))
        
        ttk.Button(button_frame, text="OK", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Initialize state of controls - Ensure color pickers are enabled
        for btn in self.grid_preset_buttons:
            if btn.winfo_exists(): btn.configure(state='normal')
        if self.custom_grid_color_button.winfo_exists(): self.custom_grid_color_button.configure(state='normal')
        if hasattr(self, 'custom_grid_color_preview_label') and self.custom_grid_color_preview_label.winfo_exists():
            self.custom_grid_color_preview_label.config(bg=self.grid_custom_color, state="normal")
        
        dialog.update_idletasks()
        dialog.minsize(dialog.winfo_reqwidth() + 20, dialog.winfo_reqheight() + 20)


    def set_grid_color_from_preset(self, color, parent_dialog):
        """Sets the grid color from a preset and updates UI."""
        self.grid_custom_color = color
        self.grid_color_mode.set("custom") # Always set to custom when picking a color
        self.grid_negative_checkbox_var.set(False) # Uncheck negative if a preset is chosen

        if hasattr(self, 'custom_grid_color_preview_label') and self.custom_grid_color_preview_label.winfo_exists():
            self.custom_grid_color_preview_label.config(bg=self.grid_custom_color, state="normal")
        
        # Ensure other controls are enabled
        for btn in self.grid_preset_buttons: # Enable preset buttons
            if btn.winfo_exists(): btn.configure(state='normal')
        if self.custom_grid_color_button.winfo_exists(): self.custom_grid_color_button.configure(state='normal')

        self.update_grid()

    def pick_grid_color_via_chooser(self, parent_dialog):
        """Open color chooser for grid, update preview and mode."""
        initial_color = self.grid_custom_color
        color_info = colorchooser.askcolor(initialcolor=initial_color, parent=parent_dialog, title="Pick Grid Color")
        
        if color_info and color_info[1]:  # If a color was chosen (hex string in color_info[1])
            new_color = color_info[1]
            self.grid_custom_color = new_color
            self.grid_color_mode.set("custom") # Ensure mode is custom
            self.grid_negative_checkbox_var.set(False) # Uncheck negative

            if hasattr(self, 'custom_grid_color_preview_label') and self.custom_grid_color_preview_label.winfo_exists():
                 self.custom_grid_color_preview_label.config(bg=new_color, state="normal")
            
            # Ensure other controls are enabled
            for btn in self.grid_preset_buttons: # Enable preset buttons
                 if btn.winfo_exists(): btn.configure(state='normal')
            if self.custom_grid_color_button.winfo_exists(): self.custom_grid_color_button.configure(state='normal')
            
            self.update_grid()
    # <<< REMOVE old pick_grid_color method, replaced by pick_grid_color_via_chooser >>>

    def update_grid(self):
        """Update the grid based on current settings."""
        self.clear_grid() # Clear existing grid first

        if not self.show_grid_var.get() or not self.current_image or not self.tk_image:
            return

        # Original image dimensions
        orig_img_width = self.current_image.width
        orig_img_height = self.current_image.height

        # Displayed tk_image dimensions
        tk_img_width = self.tk_image.width()
        tk_img_height = self.tk_image.height()

        if orig_img_width == 0 or orig_img_height == 0 or tk_img_width == 0 or tk_img_height == 0:
            return # Avoid division by zero

        # Top-left coordinate of the tk_image on the canvas
        img_left_on_canvas = self.image_x - (tk_img_width // 2)
        img_top_on_canvas = self.image_y - (tk_img_height // 2)

        # Actual canvas size of one original image pixel cell (since grid_size is 1)
        # This accounts for both the initial thumbnailing and the current zoom level
        actual_scaled_cell_w = (tk_img_width / orig_img_width) * self.grid_size
        actual_scaled_cell_h = (tk_img_height / orig_img_height) * self.grid_size

        # If scaled cell size is too small, don't draw (prevents visual clutter and performance issues)
        if actual_scaled_cell_w < 2 or actual_scaled_cell_h < 2:
            return

        # Canvas dimensions
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # Determine the range of original image pixels visible on the canvas
        # Start column index of original image pixels
        start_col = max(0, int(-img_left_on_canvas / actual_scaled_cell_w))
        # End column index (exclusive)
        end_col = min(orig_img_width, int((canvas_w - img_left_on_canvas) / actual_scaled_cell_w) + 1)

        # Start row index of original image pixels
        start_row = max(0, int(-img_top_on_canvas / actual_scaled_cell_h))
        # End row index (exclusive)
        end_row = min(orig_img_height, int((canvas_h - img_top_on_canvas) / actual_scaled_cell_h) + 1)

        # Draw vertical lines
        for i in range(start_col, end_col + 1): # Iterate through original pixel columns
            # Canvas x-coordinate for the current grid line
            line_x = img_left_on_canvas + (i * actual_scaled_cell_w)

            # Clip line to canvas bounds and image bounds on canvas
            draw_y1 = max(0, img_top_on_canvas)
            draw_y2 = min(canvas_h, img_top_on_canvas + tk_img_height)
            
            # Ensure the line is within the canvas horizontal view
            if line_x >= 0 and line_x <= canvas_w:
                # Sample color from the middle of the potential line segment within the image
                # For vertical lines, sample x at i (or i-1 if at edge), y at center of visible image
                sample_orig_x = max(0, min(i, orig_img_width - 1)) # Use current col, or previous if at right edge for sampling
                if i == end_col and i > 0 : sample_orig_x = i -1


                # Find a representative y in original image coordinates for color sampling
                # Consider the vertical center of the visible part of the image on canvas
                visible_img_center_y_on_canvas = (max(img_top_on_canvas, 0) + min(img_top_on_canvas + tk_img_height, canvas_h)) / 2
                sample_orig_y = max(0, min(int((visible_img_center_y_on_canvas - img_top_on_canvas) / actual_scaled_cell_h), orig_img_height -1))


                line_id = self.canvas.create_line(
                    line_x, draw_y1,
                    line_x, draw_y2,
                    fill=self.get_grid_color(sample_orig_x, sample_orig_y),
                    width=1
                )
                self.grid_lines.append(line_id)

        # Draw horizontal lines
        for j in range(start_row, end_row + 1): # Iterate through original pixel rows
            # Canvas y-coordinate for the current grid line
            line_y = img_top_on_canvas + (j * actual_scaled_cell_h)

            # Clip line to canvas bounds and image bounds on canvas
            draw_x1 = max(0, img_left_on_canvas)
            draw_x2 = min(canvas_w, img_left_on_canvas + tk_img_width)

            # Ensure the line is within the canvas vertical view
            if line_y >= 0 and line_y <= canvas_h:
                # Sample color
                sample_orig_y = max(0, min(j, orig_img_height - 1)) # Use current row, or previous if at bottom edge
                if j == end_row and j > 0: sample_orig_y = j-1

                visible_img_center_x_on_canvas = (max(img_left_on_canvas, 0) + min(img_left_on_canvas + tk_img_width, canvas_w)) / 2
                sample_orig_x = max(0, min(int((visible_img_center_x_on_canvas - img_left_on_canvas) / actual_scaled_cell_w), orig_img_width-1))


                line_id = self.canvas.create_line(
                    draw_x1, line_y,
                    draw_x2, line_y,
                    fill=self.get_grid_color(sample_orig_x, sample_orig_y),
                    width=1
                )
                self.grid_lines.append(line_id)

        self.root.update_idletasks()

    def get_grid_color(self, x, y):
        """Get the appropriate grid color based on mode and position."""
        # --- ADDED: Safety checks ---
        if not self.current_image: return self.grid_custom_color # Default if no image
        
        # Ensure self.grid_color_mode exists and is a tk.StringVar
        # This is less critical now as we only have one mode, but good for safety
        if not hasattr(self, 'grid_color_mode') or not isinstance(self.grid_color_mode, tk.StringVar):
            self.grid_color_mode = tk.StringVar(value="custom")
            # print("WARN get_grid_color: Re-initialized self.grid_color_mode.")

        # Negative mode logic removed.
        # Always return the custom grid color.
        
        if not hasattr(self, 'grid_custom_color') or not isinstance(self.grid_custom_color, str):
            self.grid_custom_color = "#000000" # Default to black if not set or invalid type
            # print("WARN get_grid_color: Re-initialized self.grid_custom_color to black.")
        return self.grid_custom_color

    def clear_grid(self):
        """Clear all grid lines."""
        for line_id in self.grid_lines:
            self.canvas.delete(line_id)
        self.grid_lines = []

    def toggle_grid(self):
        """Toggle the grid visibility."""
        if self.show_grid_var.get():
            self.update_grid()
        else:
            self.clear_grid()
        # Force update of the display
        self.root.update_idletasks()

    def on_preview_mode_change(self, *args):
        """Handle changes in preview mode, managing dialogs and main preview windows."""
        mode = self.preview_mode_var.get()
        self.logger.info(f"Preview mode changed to: {mode}")

        # --- Close any open settings dialogs first ---
        # (This is important if switching from one preview mode to another)
        if hasattr(self, 'crop_settings_dialog') and self.crop_settings_dialog and self.crop_settings_dialog.winfo_exists():
            if mode != "Show Crop Preview": # Close if not the target mode
                self.logger.info("Closing crop settings dialog due to mode change.")
                try: self.crop_settings_dialog.destroy()
                except tk.TclError: pass
                self.crop_settings_dialog = None

        if hasattr(self, 'last_output_settings_dialog') and self.last_output_settings_dialog and self.last_output_settings_dialog.winfo_exists():
            if mode != "Show Last Output": # Close if not the target mode
                self.logger.info("Closing last output settings dialog due to mode change.")
                try: self.last_output_settings_dialog.destroy()
                except tk.TclError: pass
                self.last_output_settings_dialog = None

        # --- Standardized Preview Window Destruction (called before setting up new mode's main windows) ---
        # This ensures live crop Toplevels are gone, or the main Last Output Toplevel is gone.
        self.destroy_all_preview_related_windows() # This method is now simplified

        # --- Recreate Windows and Set State Based on New Mode ---
        if mode == "Show Crop Preview":
            self.logger.info("Setting up 'Show Crop Preview' mode.")
            self.canvas.bind("<Motion>", self.on_mouse_move)
            # self.preview_windows will hold Toplevels for live crop previews, managed by dialog interaction
            self.preview_windows = {} 
            self.show_crop_preview_settings_dialog() # Open the settings dialog

        elif mode == "Show Last Output":
            self.logger.info("Setting up 'Show Last Output' mode.")
            self.canvas.unbind("<Motion>") 

            # Create the main container window for last output previews
            if not (hasattr(self, 'last_output_window') and self.last_output_window and self.last_output_window.winfo_exists()):
                self.last_output_window = tk.Toplevel(self.root)
                self.last_output_window.title("Last Output Preview")
                self.last_output_window.geometry("400x300") # Initial size
                self.last_output_window.resizable(True, True)
                self.last_output_window.protocol("WM_DELETE_WINDOW", self.close_last_output_window_handler)

            if not (hasattr(self, 'last_output_previews_frame') and self.last_output_previews_frame and self.last_output_previews_frame.winfo_exists()):
                self.last_output_previews_frame = ttk.Frame(self.last_output_window)
                self.last_output_previews_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                ttk.Label(self.last_output_previews_frame,
                          text="Select resolutions from settings to see previews here.",
                          anchor="center", justify="center").pack(expand=True)
            
            # self.preview_windows will hold Frames for previews within last_output_previews_frame
            self.preview_windows = {} 
            self.show_last_output_settings_dialog() # Open the settings dialog

        elif mode == "Off":
            self.logger.info("Setting up 'Off' mode (all previews disabled).")
            self.canvas.unbind("<Motion>") 
            # destroy_all_preview_related_windows() was already called.
            # Settings dialogs should have been closed at the start of this function.
            self.preview_windows = {}

        self.logger.info(f"Preview mode change to {mode} complete.")

    # Methods to open settings dialogs (called by menu)
    def open_crop_preview_settings(self):
        """Opens the crop preview settings dialog, activating mode if necessary."""
        self.logger.info("Menu command: Open Crop Preview Settings")
        if self.preview_mode_var.get() != "Show Crop Preview":
            self.preview_mode_var.set("Show Crop Preview") # This will call on_preview_mode_change
        else:
            # Mode is already active, just ensure dialog is shown/created
            self.show_crop_preview_settings_dialog()

    def open_last_output_settings(self):
        """Opens the last output settings dialog, activating mode if necessary."""
        self.logger.info("Menu command: Open Last Output Settings")
        if self.preview_mode_var.get() != "Show Last Output":
            self.preview_mode_var.set("Show Last Output") # This will call on_preview_mode_change
        else:
            # Mode is already active, just ensure dialog is shown/created
            self.show_last_output_settings_dialog()

    def destroy_all_preview_related_windows(self):
        """Helper to destroy all types of preview windows (Toplevels and main Last Output window)."""
        self.logger.info("Attempting to destroy all preview related windows.")
        # Crop Preview Toplevels (stored in self.preview_windows when in crop mode)
        if hasattr(self, 'preview_windows') and self.preview_windows:
            for idx, window in list(self.preview_windows.items()): # Iterate over a copy
                if isinstance(window, tk.Toplevel) and window.winfo_exists():
                    try:
                        window.destroy()
                        self.logger.info(f"  Destroyed crop preview Toplevel for index {idx}.")
                    except tk.TclError as e:
                        self.logger.warning(f"  Error destroying crop Toplevel {idx}: {e}")
        self.preview_windows = {} # Clear it regardless of what it held

        # Main Last Output Toplevel Window
        if hasattr(self, 'last_output_window') and self.last_output_window and self.last_output_window.winfo_exists():
            try:
                self.last_output_window.destroy()
                self.logger.info("  Destroyed last_output_window.")
            except tk.TclError as e:
                self.logger.warning(f"  Error destroying last_output_window: {e}")
        self.last_output_window = None
        if hasattr(self, 'last_output_previews_frame'): # check before setting None
            self.last_output_previews_frame = None

        # Settings Dialogs - REMOVED, as dialogs themselves are removed
        # if hasattr(self, 'crop_settings_dialog') ...
        # if hasattr(self, 'last_output_settings_dialog') ...

        self.logger.info("Finished destroying preview related windows.")

    def close_last_output_window_and_dialog(self):
        """Handles closing the last output window, also turns off mode if appropriate."""
        self.logger.info("Last output window closed by user.")
        if hasattr(self, 'last_output_window') and self.last_output_window and self.last_output_window.winfo_exists():
            self.last_output_window.destroy()
        self.last_output_window = None
        
        # Also close the settings dialog if it's open
        if hasattr(self, 'last_output_settings_dialog') and self.last_output_settings_dialog and self.last_output_settings_dialog.winfo_exists():
            self.logger.info("Also closing associated last output settings dialog.")
            try: self.last_output_settings_dialog.destroy()
            except tk.TclError: pass
            self.last_output_settings_dialog = None

        # If this was the active mode, switch to "Off"
        if self.preview_mode_var.get() == "Show Last Output":
            self.preview_mode_var.set("Off") # This will trigger on_preview_mode_change again

    # Renamed from close_last_output_window_and_dialog to avoid confusion with a method of similar name
    def close_last_output_window_handler(self):
        """Protocol handler for WM_DELETE_WINDOW on the main last_output_window."""
        self.logger.info("Main last_output_window WM_DELETE_WINDOW invoked.")
        # This simply calls the more comprehensive cleanup method
        self.close_last_output_window_and_dialog()

    def show_crop_preview_settings_dialog(self):
        """Creates and shows the settings dialog for live crop previews."""
        if not TARGET_SIZE:
            messagebox.showwarning("No Resolutions Set", 
                                 "Target resolutions are not defined. Please set them via File > Change Resolution.", 
                                 parent=self.root)
            if self.preview_mode_var.get() == "Show Crop Preview":
                self.preview_mode_var.set("Off") # Revert mode if it was just activated
            return

        if hasattr(self, 'crop_settings_dialog') and self.crop_settings_dialog and self.crop_settings_dialog.winfo_exists():
            self.crop_settings_dialog.lift()
            self.crop_settings_dialog.focus_force()
            return

        self.crop_settings_dialog = tk.Toplevel(self.root)
        self.crop_settings_dialog.title("Crop Preview Settings")
        self.crop_settings_dialog.transient(self.root)
        # self.crop_settings_dialog.grab_set() # Make modal if preferred

        # Initialize/Re-initialize dialog-specific boolean vars based on current TARGET_SIZE
        # This ensures the dialog always reflects the available resolutions.
        # self.crop_preview_dialog_vars = [tk.BooleanVar(value=True) for _ in TARGET_SIZE] # OLD

        # Initialize/Re-initialize dialog-specific boolean vars.
        # Try to reuse existing vars if possible to preserve their checked/unchecked state
        # if the dialog is closed and reopened.
        if not hasattr(self, 'crop_preview_dialog_vars') or \
           not isinstance(self.crop_preview_dialog_vars, list) or \
           len(self.crop_preview_dialog_vars) != len(TARGET_SIZE) or \
           not all(isinstance(v, tk.BooleanVar) for v in self.crop_preview_dialog_vars):
            # If vars don't exist, aren't a list, length mismatch, or not all BooleanVars, reinitialize.
            # Default to True (checked) for newly initialized or mismatched sets.
            self.logger.critical("CRITICAL_LOG: Re-initializing self.crop_preview_dialog_vars to all True in show_crop_preview_settings_dialog. Check call stack if unexpected.") # ADDED LOG
            if not TARGET_SIZE: # Defensive check if TARGET_SIZE is somehow empty
                self.logger.warning("CRITICAL_LOG: TARGET_SIZE is empty/None during crop_preview_dialog_vars re-initialization in show_crop_preview_settings_dialog.")
                self.crop_preview_dialog_vars = []
            else:
                self.crop_preview_dialog_vars = [tk.BooleanVar(value=True) for _ in TARGET_SIZE]
        else:
            # Vars exist, match length, and are BooleanVars. Reuse them.
            self.logger.info("Reusing existing crop_preview_dialog_vars for crop settings dialog.")

        main_frame = ttk.Frame(self.crop_settings_dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Select resolutions for live crop preview:").pack(pady=(0, 10))
        
        res_frame = ttk.Frame(main_frame)
        res_frame.pack(pady=5, padx=10, fill="x", expand=True)

        for i, (w, h) in enumerate(TARGET_SIZE):
            var = self.crop_preview_dialog_vars[i]
            # The command directly calls the handler for toggling a single preview window
            cb = ttk.Checkbutton(res_frame, text=f"{w}x{h}", variable=var, 
                                 command=lambda idx=i, v=var: self._toggle_single_crop_preview_window(idx, v.get()))
            cb.pack(anchor="w")

        def on_dialog_close_button():
            self.logger.info("Crop preview settings dialog 'Close' button clicked.")
            if self.crop_settings_dialog and self.crop_settings_dialog.winfo_exists():
                self.crop_settings_dialog.destroy()
            self.crop_settings_dialog = None
            # Closing this dialog does NOT automatically turn off the "Show Crop Preview" mode.
            # The live previews will remain as per the last settings until the mode is changed or app closes.

        ttk.Button(main_frame, text="Close", command=on_dialog_close_button).pack(pady=(10,0))
        self.crop_settings_dialog.protocol("WM_DELETE_WINDOW", on_dialog_close_button)
        
        # Position dialog
        self.crop_settings_dialog.update_idletasks()
        x = self.root.winfo_x() + 50
        y = self.root.winfo_y() + 50
        self.crop_settings_dialog.geometry(f"+{x}+{y}")
        self.crop_settings_dialog.focus_force()
        self.logger.info("Crop preview settings dialog shown.")

        # Initial creation/update of preview windows based on default dialog var states (all true)
        if self.current_image and hasattr(self, 'cursor_x') and hasattr(self, 'cursor_y'):
             self._update_all_crop_previews_based_on_dialog(self.cursor_x, self.cursor_y)

    def _toggle_single_crop_preview_window(self, idx, is_checked):
        """Shows or hides a single live crop preview Toplevel window based on dialog checkbox."""
        self.logger.info(f"Crop preview for index {idx} ({TARGET_SIZE[idx][0]}x{TARGET_SIZE[idx][1]}) toggled to {is_checked} from dialog.")

        if not is_checked:
            # If unchecked, close the specific Toplevel preview window
            if idx in self.preview_windows:
                window_to_close = self.preview_windows.get(idx)
                if isinstance(window_to_close, tk.Toplevel) and window_to_close.winfo_exists():
                    self.logger.info(f"Closing crop preview Toplevel for index {idx} via dialog toggle.")
                    try: window_to_close.destroy()
                    except tk.TclError as e: self.logger.warning(f"Error destroying crop Toplevel {idx}: {e}")
                # Remove from dict even if destroy failed, to avoid issues
                del self.preview_windows[idx] 
        else:
            # If checked, and mouse is over image, create/update the preview window.
            # update_preview_windows will handle this using crop_preview_dialog_vars.
            if self.current_image and hasattr(self, 'cursor_x') and hasattr(self, 'cursor_y') and \
               (0 <= self.cursor_x < self.current_image.width and 0 <= self.cursor_y < self.current_image.height):
                self.logger.info(f"Checkbox for crop preview index {idx} checked. Triggering update.")
                # Call the main updater which iterates through all dialog vars
                self._update_all_crop_previews_based_on_dialog(self.cursor_x, self.cursor_y)
            else:
                self.logger.info(f"Checkbox for crop preview index {idx} checked, but no valid cursor coords. Will update on mouse move.")

    def _update_all_crop_previews_based_on_dialog(self, center_x, center_y):
        """Updates all live crop preview Toplevels based on self.crop_preview_dialog_vars and mouse coords."""
        if not (self.preview_mode_var.get() == "Show Crop Preview" and self.current_image):
            return # Not in the right mode or no image
        if not (hasattr(self, 'cursor_x') and hasattr(self, 'cursor_y')):
            return # No valid cursor position tracked yet
        if not (0 <= center_x < self.current_image.width and 0 <= center_y < self.current_image.height):
             # If current coords are outside image, behavior might be to clear or hide previews.
             # For now, let's just not update with invalid coords for creation.
             # Existing windows will remain until next valid mouse_move within image.
            self.logger.debug("_update_all_crop_previews: center coords outside image, skipping update.")
            # Consider clearing existing previews if mouse moves outside image:
            # for idx_open in list(self.preview_windows.keys()):
            #     window_to_close = self.preview_windows.get(idx_open)
            #     if isinstance(window_to_close, tk.Toplevel) and window_to_close.winfo_exists():
            #         window_to_close.destroy()
            #     del self.preview_windows[idx_open]
            return

        if not hasattr(self, 'crop_preview_dialog_vars') or len(self.crop_preview_dialog_vars) != len(TARGET_SIZE):
            self.logger.warning("_update_all_crop_previews: crop_preview_dialog_vars mismatch or not found.")
            return

        # Determine which resolutions are selected in the dialog
        selected_indices_from_dialog = []
        self.logger.debug(f"_update_all_crop_previews: Building selected_indices. Vars count: {len(self.crop_preview_dialog_vars) if hasattr(self, 'crop_preview_dialog_vars') else 'N/A'}")
        if hasattr(self, 'crop_preview_dialog_vars') and isinstance(self.crop_preview_dialog_vars, list):
            for i, var in enumerate(self.crop_preview_dialog_vars):
                if isinstance(var, tk.BooleanVar): # Ensure it's a BooleanVar before calling get()
                    var_state = var.get()
                    self.logger.debug(f"  Var index {i} ({TARGET_SIZE[i][0]}x{TARGET_SIZE[i][1]}): state is {var_state}")
                    if var_state:
                        selected_indices_from_dialog.append(i)
                else:
                    self.logger.warning(f"  Var index {i} is not a BooleanVar: {type(var)}. Skipping.")
        self.logger.debug(f"_update_all_crop_previews: selected_indices_from_dialog: {selected_indices_from_dialog}")
        self.logger.debug(f"_update_all_crop_previews: current self.preview_windows keys: {list(self.preview_windows.keys())}")
        
        # Close Toplevels for resolutions that are no longer selected in the dialog
        for idx_open in list(self.preview_windows.keys()): # Iterate over a copy of keys
            if idx_open not in selected_indices_from_dialog:
                window_to_close = self.preview_windows.get(idx_open)
                if isinstance(window_to_close, tk.Toplevel) and window_to_close.winfo_exists():
                    self.logger.info(f"Closing unselected crop preview Toplevel for index {idx_open}.")
                    try: window_to_close.destroy()
                    except tk.TclError as e: self.logger.warning(f"Error destroying crop Toplevel {idx_open}: {e}")
                if idx_open in self.preview_windows: del self.preview_windows[idx_open]

        # Update or create Toplevels for resolutions selected in the dialog
        for idx_selected in selected_indices_from_dialog:
            w, h = TARGET_SIZE[idx_selected]
            preview_window = self.preview_windows.get(idx_selected)

            if not (preview_window and isinstance(preview_window, tk.Toplevel) and preview_window.winfo_exists()):
                self.logger.info(f"Creating new crop preview Toplevel for index {idx_selected} ({w}x{h}).")
                preview_window = tk.Toplevel(self.root)
                preview_window.title(f"Crop Preview {w}x{h} (Live)")
                preview_window.protocol("WM_DELETE_WINDOW", 
                    lambda i=idx_selected: self._handle_single_crop_Toplevel_closed_by_user(i))
                
                preview_window.resizable(True, True)
                # Basic structure for the preview content (label within frames)
                content_main_frame = ttk.Frame(preview_window, padding="10 30 10 10") # Padding for title area
                content_main_frame.pack(fill=tk.BOTH, expand=True)
                centering_frame = ttk.Frame(content_main_frame)
                centering_frame.pack(fill=tk.BOTH, expand=True)
                centering_frame.grid_rowconfigure(0, weight=1)
                centering_frame.grid_columnconfigure(0, weight=1)
                actual_preview_frame = ttk.Frame(centering_frame, width=w, height=h)
                actual_preview_frame.grid(row=0, column=0)
                actual_preview_frame.grid_propagate(False)
                preview_label = ttk.Label(actual_preview_frame)
                preview_label.place(relx=0.5, rely=0.5, anchor="center")
                        
                preview_window.preview_label = preview_label
                preview_window.original_width = w
                preview_window.original_height = h
                
                self.preview_windows[idx_selected] = preview_window
                # Set initial size of the Toplevel
                geom_w = w + 40 # Approx padding for borders
                geom_h = h + 80 # Approx padding for title bar and borders
                preview_window.geometry(f"{geom_w}x{geom_h}")
            
            # This updates the image content of the preview_label in the Toplevel
            self.update_preview_image(idx_selected, center_x, center_y)

    def _handle_single_crop_Toplevel_closed_by_user(self, idx):
        """Called when a user closes a single live crop preview Toplevel window directly (e.g., via 'X' button)."""
        self.logger.info(f"User clicked 'X' on crop preview Toplevel for index {idx} (WM_DELETE_WINDOW).")

        # Get a reference to the window *before* removing it from the dictionary.
        window_to_destroy = self.preview_windows.get(idx)

        # Remove the window from active tracking.
        if idx in self.preview_windows:
            self.logger.debug(f"Removing preview window for index {idx} from self.preview_windows list.")
            del self.preview_windows[idx]
        else:
            self.logger.warning(f"WM_DELETE_WINDOW for index {idx}, but it was not found in self.preview_windows. It might have been closed by other means.")
        
        # Uncheck the corresponding checkbox in the settings dialog if the dialog exists.
        # This will trigger the checkbox's command (_toggle_single_crop_preview_window).
        # That command checks `if idx in self.preview_windows` before trying to destroy,
        # so it should not re-destroy here because we've just deleted it from the dict.
        # --- MODIFICATION: Update the BooleanVar directly, regardless of dialog visibility ---
        if hasattr(self, 'crop_preview_dialog_vars') and isinstance(self.crop_preview_dialog_vars, list) and idx < len(self.crop_preview_dialog_vars):
            if isinstance(self.crop_preview_dialog_vars[idx], tk.BooleanVar): # Ensure it is a BooleanVar
                if self.crop_preview_dialog_vars[idx].get(): # Only set if it's currently True
                    self.logger.info(f"Setting crop_preview_dialog_vars[{idx}] to False as its window is being closed.")
                    self.crop_preview_dialog_vars[idx].set(False)
                else:
                    self.logger.debug(f"crop_preview_dialog_vars[{idx}] was already False.")
            else:
                self.logger.warning(f"crop_preview_dialog_vars[{idx}] is not a BooleanVar. Cannot update state.")
        else:
            self.logger.warning(f"Could not update crop_preview_dialog_vars for index {idx} (list missing, not list, or index out of bounds).")
        # --- END MODIFICATION ---
        
        # Now, explicitly destroy the window if we have a valid reference and it still exists.
        if window_to_destroy and window_to_destroy.winfo_exists():
            try:
                self.logger.info(f"Explicitly calling destroy() on crop preview Toplevel for index {idx}.")
                window_to_destroy.destroy()
            except tk.TclError as e_destroy:
                self.logger.error(f"TclError while explicitly destroying crop preview Toplevel {idx}: {e_destroy}")
        elif window_to_destroy:
            self.logger.info(f"Crop preview Toplevel for index {idx} was already destroyed before explicit call in WM_DELETE_WINDOW handler.")
        else:
            self.logger.warning(f"Could not explicitly destroy crop preview Toplevel for index {idx} because no valid window reference was found (was not in self.preview_windows). ")

    def show_last_output_settings_dialog(self):
        """Creates and shows the settings dialog for the last output previews."""
        if not TARGET_SIZE:
            messagebox.showwarning("No Resolutions Set", 
                                 "Target resolutions are not defined. Please set them via File > Change Resolution.", 
                                 parent=self.root)
            if self.preview_mode_var.get() == "Show Last Output":
                self.preview_mode_var.set("Off") # Revert mode
            return

        if hasattr(self, 'last_output_settings_dialog') and self.last_output_settings_dialog and self.last_output_settings_dialog.winfo_exists():
            self.last_output_settings_dialog.lift()
            self.last_output_settings_dialog.focus_force()
            return

        self.last_output_settings_dialog = tk.Toplevel(self.root)
        self.last_output_settings_dialog.title("Last Output Settings")
        self.last_output_settings_dialog.transient(self.root)
        # Not grabbing set, so user can interact with the main Last Output window if it's also open.

        # Initialize/Re-initialize dialog-specific boolean vars
        self.last_output_dialog_vars = [tk.BooleanVar(value=True) for _ in TARGET_SIZE]

        main_frame = ttk.Frame(self.last_output_settings_dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Select resolutions to display in Last Output Preview window:").pack(pady=(0,10))
        
        res_frame = ttk.Frame(main_frame)
        res_frame.pack(pady=5, padx=10, fill="x", expand=True)

        for i, (w, h) in enumerate(TARGET_SIZE):
            var = self.last_output_dialog_vars[i]
            # Command directly refreshes the content of the main last output window
            cb = ttk.Checkbutton(res_frame, text=f"{w}x{h}", variable=var, 
                                 command=self._refresh_last_output_previews_from_dialog_vars)
            cb.pack(anchor="w")
        
        def on_dialog_close_button():
            self.logger.info("Last output settings dialog 'Close' button clicked.")
            if self.last_output_settings_dialog and self.last_output_settings_dialog.winfo_exists():
                self.last_output_settings_dialog.destroy()
            self.last_output_settings_dialog = None
            # Closing this settings dialog does NOT close the main Last Output Preview window
            # or change the preview mode.

        ttk.Button(main_frame, text="Close", command=on_dialog_close_button).pack(pady=(10,0))
        self.last_output_settings_dialog.protocol("WM_DELETE_WINDOW", on_dialog_close_button)

        # Position dialog
        self.last_output_settings_dialog.update_idletasks()
        x = self.root.winfo_x() + 70 # Offset slightly differently from crop settings
        y = self.root.winfo_y() + 70
        self.last_output_settings_dialog.geometry(f"+{x}+{y}")
        self.last_output_settings_dialog.focus_force()
        self.logger.info("Last output settings dialog shown.")

        # Initial refresh of the main Last Output Preview window based on default dialog selections
        if self.preview_mode_var.get() == "Show Last Output":
            self._refresh_last_output_previews_from_dialog_vars()

    def _refresh_last_output_previews_from_dialog_vars(self):
        """Refreshes the content of the main self.last_output_window based on self.last_output_dialog_vars."""
        if not (self.preview_mode_var.get() == "Show Last Output" and 
                hasattr(self, 'last_output_window') and self.last_output_window and self.last_output_window.winfo_exists() and
                hasattr(self, 'last_output_previews_frame') and self.last_output_previews_frame and self.last_output_previews_frame.winfo_exists()):
            self.logger.debug("_refresh_last_output_previews_from_dialog_vars: Conditions not met for refresh (mode not active or windows missing).")
            return

        if not hasattr(self, 'last_output_dialog_vars') or len(self.last_output_dialog_vars) != len(TARGET_SIZE):
            self.logger.warning("_refresh_last_output_previews_from_dialog_vars: last_output_dialog_vars mismatch or not found.")
            return

        # Clear existing previews in the frame
        for widget in self.last_output_previews_frame.winfo_children():
            widget.destroy()
        self.preview_windows = {} # Reset dictionary for Frames that are children of last_output_previews_frame

        max_width_needed = 0
        total_height_needed = 0
        padding_between_previews = 10 # Reduced padding a bit
        any_preview_shown = False

        for i, (w, h) in enumerate(TARGET_SIZE):
            if self.last_output_dialog_vars[i].get(): # Check if this resolution is selected in the dialog
                any_preview_shown = True
                # self.update_last_output_preview(w, h) creates and packs a frame (containing a label and canvas)
                # into self.last_output_previews_frame. It also stores a reference to this frame
                # in self.preview_windows[(w,h)].
                self.update_last_output_preview(w, h) 

                # Estimate size contribution for resizing the main last_output_window
                est_frame_width = w + 22  # Approx canvas width + internal padding/border
                est_frame_height = h + 52 # Approx canvas height + label height + internal padding/border
                max_width_needed = max(max_width_needed, est_frame_width)
                total_height_needed += est_frame_height + padding_between_previews

        if not any_preview_shown:
             ttk.Label(self.last_output_previews_frame,
                       text="No resolutions selected in settings. Previews will appear here after processing an image for selected resolutions.",
                       anchor="center", justify="center", wraplength=280).pack(expand=True, pady=10)
             final_width = 300 # Default size if no previews are shown
             final_height = 150
        else:
            min_title_width = 200 # Fallback for title width
            try:
                title_font = tk.font.nametofont("TkDefaultFont").copy()
                min_title_width = title_font.measure(self.last_output_window.title()) + 40
            except Exception: pass

            final_width = max(max_width_needed + 40, min_title_width, 250) # Outer window padding, ensure min width
            final_height = max(total_height_needed - padding_between_previews + 40, 150) # Correct total height, ensure min height
        
        self.logger.info(f"Resizing last_output_window to {final_width}x{final_height} based on dialog vars.")
        self.apply_geometry_safely(self.last_output_window, final_width, final_height)
        # self.last_output_window.update_idletasks() # May not be needed if apply_geometry_safely handles it

    def apply_geometry_safely(self, window, width, height):
        """Apply geometry only if the window still exists."""
        try:  # 4 spaces indentation
            if window and window.winfo_exists():  # 8 spaces indentation
                window.geometry(f"{width}x{height}") # 12 spaces indentation
                print(f"DEBUG apply_geometry_safely: Set geometry {width}x{height}") # 12 spaces indentation
            else:  # 8 spaces indentation (aligned with 'if')
                print(f"WARN apply_geometry_safely: Window destroyed before geometry could be set.") # 12 spaces indentation
        except tk.TclError as e:  # 4 spaces indentation (aligned with 'try')
            print(f"ERROR apply_geometry_safely: TclError setting geometry: {e}") # 8 spaces indentation

    def _setup_output_folder(self):
        """Asks the user if they want a timestamped output folder and sets it up."""
        try:
            use_timestamp = messagebox.askyesno(
                "New Output Subfolder",
                "Do you want to create a timestamped output folder inside 'output_resized'?",
                parent=self.root
            )

            base_output_root = os.path.join(get_base_path(), "output_resized")
            os.makedirs(base_output_root, exist_ok=True)

            if use_timestamp:
                timestamp = datetime.now().strftime("%y-%m-%d_%H-%M") # Updated format
                self.output_folder = os.path.join(base_output_root, timestamp)
                # Ensure the specific timestamped folder is created if chosen
                os.makedirs(self.output_folder, exist_ok=True)
                self.logger.info(f"Output folder will be timestamped: {self.output_folder}")
            else:
                self.output_folder = base_output_root
                self.logger.info(f"Output folder will be: {self.output_folder}")
            
            # This part was in change_output_folder apply, seems relevant here too for first-time setup
            if not os.path.exists(self.output_folder):
                 os.makedirs(self.output_folder, exist_ok=True)


        except Exception as e:
            self.logger.error(f"Error setting up output folder: {str(e)}")
            messagebox.showerror("Output Folder Error", f"Failed to set up output folder: {str(e)}", parent=self.root)
            # Fallback to a non-timestamped default if setup fails
            self.output_folder = os.path.join(get_base_path(), "output_resized")
            os.makedirs(self.output_folder, exist_ok=True)


    def _open_single_file_action(self):
        """Handles the logic for opening a single image file."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select Image File",
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.bmp"),
                    ("All files", "*.*")
                ]
            )
            if file_path:
                self.image_paths = [file_path]
                self.current_index = 0
                self.show_image()
                self.logger.info(f"Opened image: {file_path}")
                self.base_folder = os.path.dirname(file_path)

                # --- Call the new output folder setup method ---
                self._setup_output_folder()
                # --- END ---

                # Ensure window is wide enough after loading images
                self.root.update_idletasks()
                current_width = self.root.winfo_width()
                if current_width < 400:
                    self.root.geometry(f"400x{self.root.winfo_height()}")
        except Exception as e:
            self.logger.warning(f"Error opening single file: {str(e)}")
            messagebox.showerror("Error", f"Failed to open image file: {str(e)}", parent=self.root)

    def _open_image_folder_action(self):
        """Handles the logic for opening a folder of images, including output folder setup."""
        try:
            folder_path = filedialog.askdirectory(title="Select Folder of Images", parent=self.root)
            if folder_path:
                self.base_folder = folder_path  # Set base_folder

                # --- Call the new output folder setup method ---
                self._setup_output_folder()
                # --- END ---

                self.image_paths = []  # Clear existing images
                # Use self.base_folder for os.walk
                for root_dir, _, files in os.walk(self.base_folder):
                    for file in files:
                        if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                            self.image_paths.append(os.path.join(root_dir, file))
                
                if self.image_paths:
                    self.current_index = 0
                    self.show_image()
                    self.logger.info(f"Opened folder: {folder_path} with {len(self.image_paths)} images")

                    # Ensure window is wide enough after loading images
                    self.root.update_idletasks()
                    current_width = self.root.winfo_width()
                    if current_width < 400:
                        self.root.geometry(f"400x{self.root.winfo_height()}")
                else:
                    messagebox.showwarning("No Images", "No image files found in the selected folder.", parent=self.root)
            # If folder_path is None (user cancelled dialog), do nothing further for this action.

        except Exception as e:
            self.logger.warning(f"Error opening image folder: {str(e)}")
            messagebox.showerror("Error", f"Failed to open image folder: {str(e)}", parent=self.root)

    def change_output_folder(self):
        """Open dialog to change the output folder."""
        try:
            # Create dialog window
            dialog = tk.Toplevel(self.root)
            dialog.title("Change Output Folder")
            dialog.geometry("450x200") # Fixed size for this dialog
            dialog.resizable(False, False)
            dialog.grab_set()  # Make window modal
            dialog.transient(self.root) # Associate with root window
            
            # Define variables
            # Check if current output_folder is the default one
            # is_default_output = (self.output_folder == os.path.join(get_base_path(), "output_resized")) # No longer needed for default checkmark
            use_default_var = tk.BooleanVar(value=True) # <<< SET TO TRUE FOR DEFAULT CHECKED >>>
            current_folder_var = tk.StringVar(value=self.output_folder)
            
            # Create main frame
            main_frame = ttk.Frame(dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create use default checkbox
            default_check = ttk.Checkbutton(
                main_frame, 
                text=f"Use default directory (output_resized inside script folder)",
                variable=use_default_var,
                command=lambda: self.toggle_path_widgets(path_entry, browse_button, use_default_var.get(), current_folder_var)
            )
            default_check.pack(anchor=tk.W, pady=(0, 10))
            
            # Create file directory section
            path_frame = ttk.LabelFrame(main_frame, text="Custom Output Directory")
            path_frame.pack(fill=tk.X, pady=10)
            
            # Entry for path display
            path_entry = ttk.Entry(path_frame, textvariable=current_folder_var, width=40)
            path_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
            
            # Browse button
            browse_button = ttk.Button(
                path_frame,
                text="Browse...",
                command=lambda: self.select_output_folder(current_folder_var) # This calls the existing method
            )
            browse_button.pack(side=tk.RIGHT, padx=5, pady=5)
            
            # Bottom buttons
            button_frame_bottom = ttk.Frame(main_frame) # Renamed to avoid clash if any
            button_frame_bottom.pack(fill=tk.X, pady=(20, 0), side=tk.BOTTOM)
            
            cancel_button = ttk.Button(
                button_frame_bottom,
                text="Cancel",
                command=dialog.destroy
            )
            cancel_button.pack(side=tk.RIGHT, padx=5)
            
            ok_button = ttk.Button(
                button_frame_bottom,
                text="OK",
                command=lambda: self.apply_output_folder(
                    use_default_var.get(), 
                    current_folder_var.get(),
                    dialog # Pass dialog to be destroyed by apply_output_folder
                )
            )
            ok_button.pack(side=tk.RIGHT, padx=5)
            
            # Initialize state of path_entry and browse_button
            self.toggle_path_widgets(path_entry, browse_button, use_default_var.get(), current_folder_var)
            
            dialog.wait_window() # Wait for this dialog to close

        except Exception as e:
            self.logger.warning(f"Error showing output folder dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to show output folder dialog: {str(e)}", parent=self.root)
    
    def toggle_path_widgets(self, entry_widget, button_widget, use_default_bool, folder_str_var):
        """Toggle state of path-related widgets and updates folder_str_var if default is chosen."""
        default_path = os.path.join(get_base_path(), "output_resized")
        if use_default_bool:
            entry_widget.configure(state="disabled")
            button_widget.configure(state="disabled")
            folder_str_var.set(default_path) # Set text to default path
        else:
            entry_widget.configure(state="normal")
            button_widget.configure(state="normal")
            # If current_folder_var still holds default path when switching to custom, user might want to clear it or select new
            # For now, it just enables, user has to change it if it was default.

    def select_output_folder(self, folder_var):
        """Open folder browser dialog and update path variable."""
        # Ensure the parent is set for the dialog
        folder = filedialog.askdirectory(title="Select Output Folder", parent=self.root) 
        if folder:
            folder_var.set(folder)
    
    def apply_output_folder(self, use_default, custom_folder_path, dialog_to_destroy):
        """Apply the output folder settings and close dialog."""
        try:
            if use_default:
                self.output_folder = os.path.join(get_base_path(), "output_resized")
            else:
                # Validate custom_folder_path
                if not custom_folder_path or not isinstance(custom_folder_path, str):
                    messagebox.showerror("Invalid Path", "Custom folder path is not valid.", parent=dialog_to_destroy)
                    return # Don't close dialog
                
                if os.path.isdir(custom_folder_path):
                    self.output_folder = custom_folder_path
                else:
                    # Ask user if they want to create it
                    if messagebox.askyesno("Create Folder?", f"The path '{custom_folder_path}' does not exist or is not a directory. Create it?", parent=dialog_to_destroy):
                        try:
                            os.makedirs(custom_folder_path, exist_ok=True)
                            self.output_folder = custom_folder_path
                        except Exception as e_create:
                            self.logger.error(f"Failed to create directory {custom_folder_path}: {e_create}")
                            messagebox.showerror("Creation Failed", f"Could not create directory: {e_create}", parent=dialog_to_destroy)
                            return # Don't close dialog
                    else:
                        return # User chose not to create, so don't close dialog
            
            # Ensure the final output folder exists (might be redundant if created above, but safe)
            os.makedirs(self.output_folder, exist_ok=True)
            self.logger.info(f"Output folder set to: {self.output_folder}")
            messagebox.showinfo("Output Folder Set", f"Output folder has been set to:\\n{self.output_folder}", parent=self.root) # Parent to root
            dialog_to_destroy.destroy()
            
        except Exception as e:
            self.logger.warning(f"Error setting output folder: {str(e)}")
            # Ensure parent is the dialog if it still exists, otherwise root
            parent_for_error = dialog_to_destroy if dialog_to_destroy.winfo_exists() else self.root
            messagebox.showerror("Error", f"Failed to set output folder: {str(e)}", parent=parent_for_error)

    def shorten_path(self, path_to_shorten):
        """Shorten a path for display, e.g., 'C:\\\\User\\\\...\\\\Folder'."""
        try:
            if not path_to_shorten or not isinstance(path_to_shorten, str):
                return "Invalid Path"
                
            drive, tail = os.path.splitdrive(path_to_shorten)
            # Normalize separators for reliable splitting
            normalized_tail = tail.replace("\\\\", os.sep).replace("/", os.sep)
            components = [c for c in normalized_tail.split(os.sep) if c] # Filter out empty strings from multiple slashes
            
            if not components: # Path was just a drive or empty after drive
                return drive + os.sep if drive else ""

            if len(components) <= 2: # If path has 1 folder level or less (plus filename/last_component)
                return os.path.join(drive, *components) if drive else os.path.join(*components)
            
            # Show Drive:\\\\components[0]\\\\...\\\\components[-1] (if components[0] is first folder)
            return os.path.join(drive, components[0], "...", components[-1]) if drive else os.path.join(components[0], "...", components[-1])
        except Exception as e_shorten:
            self.logger.error(f"Error shortening path '{path_to_shorten}': {e_shorten}")
            return path_to_shorten # Fallback to original path if any error

    def crosshair_options_dialog(self):
        """Show the crosshair options dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Crosshair Options")
        dialog.transient(self.root)
        dialog.grab_set()
        # dialog.resizable(False, False) # Allow resizing if content needs it
        
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Type section
        type_frame = ttk.LabelFrame(main_frame, text="Crosshair Type", padding="10")
        type_frame.pack(fill=tk.X, pady=(0, 10))

        def _update_crosshair_and_size_entry_state():
            # This internal helper ensures UI consistency when type/settings change
            if hasattr(self, 'crosshair_size_entry'): # Check if entry exists
                if self.crosshair_type.get() == "cross":
                    self.crosshair_size_entry.config(state="normal")
                else:
                    self.crosshair_size_entry.config(state="disabled")
            self.update_crosshair() # Redraw crosshair on canvas

        ttk.Radiobutton(
            type_frame, text="Pixel (single square)", variable=self.crosshair_type, value="pixel", command=_update_crosshair_and_size_entry_state
        ).pack(anchor=tk.W)
        
        cross_specific_frame = ttk.Frame(type_frame)
        cross_specific_frame.pack(fill=tk.X, anchor=tk.W)
        ttk.Radiobutton(
            cross_specific_frame, text="Cross (+ pattern)    Size (pixels):", variable=self.crosshair_type, value="cross", command=_update_crosshair_and_size_entry_state
        ).pack(side=tk.LEFT, anchor=tk.W)
        
        self.crosshair_size_entry = ttk.Entry(cross_specific_frame, textvariable=self.crosshair_size, width=4)
        self.crosshair_size_entry.pack(side=tk.LEFT, padx=5)

        # Color Section
        color_section_frame = ttk.LabelFrame(main_frame, text="Crosshair Color", padding="10")
        color_section_frame.pack(fill=tk.X, pady=(0,10))

        preset_buttons_frame = ttk.Frame(color_section_frame)
        preset_buttons_frame.pack(fill=tk.X, pady=(0,5))
        common_colors = { # Using a more common set for brevity in dialog
            "Black": "#000000", "White": "#FFFFFF", "Red": "#FF0000", 
            "Green": "#00FF00", "Blue": "#0000FF", "Yellow": "#FFFF00"
        }
        for name, hex_val in common_colors.items():
            btn = tk.Button(preset_buttons_frame, text=name, bg=hex_val, 
                            fg="white" if self.is_dark_color(hex_val) else "black", 
                            width=6, command=lambda c=hex_val: self.set_crosshair_color(c))
            btn.pack(side=tk.LEFT, padx=2, pady=2) # Added pady

        custom_color_frame = ttk.Frame(color_section_frame)
        custom_color_frame.pack(fill=tk.X, pady=5)
        tk.Button(custom_color_frame, text="Pick Custom Color...", command=self.pick_crosshair_color).pack(side=tk.LEFT, padx=(0,10))
        
        # Ensure self.crosshair_color_preview_label is created here if it can be None otherwise
        if not hasattr(self, 'crosshair_color_preview_label') or not self.crosshair_color_preview_label.winfo_exists():
            self.crosshair_color_preview_label = tk.Label(custom_color_frame, text=" ", width=10, relief="sunken", bd=1)
        self.crosshair_color_preview_label.pack(side=tk.LEFT)
        
        ttk.Checkbutton(
            color_section_frame, text="Use Negative Colors (inverts pixel colors)", 
            variable=self.crosshair_use_negative, 
            command=self.update_negative_state # This should also update the preview label
        ).pack(anchor=tk.W, pady=(5,0))

        # OK Button
        ok_button_frame = ttk.Frame(main_frame)
        ok_button_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Button(ok_button_frame, text="OK", command=dialog.destroy).pack()

        # Initial UI state update based on current settings
        _update_crosshair_and_size_entry_state()
        self.update_negative_state() # Updates color preview based on negative state

        # Position dialog relative to root window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_reqwidth() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_reqheight() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.focus_force()

    def pick_crosshair_color(self):
        """Open color chooser dialog for crosshair color."""
        parent_window = self.root
        # Try to find the active crosshair options dialog to parent the color chooser to it
        # This makes the UI flow better (color chooser on top of its settings dialog)
        if hasattr(self, 'crosshair_options_dialog_window') and self.crosshair_options_dialog_window.winfo_exists():
             parent_window = self.crosshair_options_dialog_window
        elif hasattr(self.root, 'focus_get') and isinstance(self.root.focus_get(), tk.Toplevel):
             # Fallback: parent to currently focused Toplevel if it might be the dialog
             current_focus = self.root.focus_get()
             if current_focus.title() == "Crosshair Options": # Check title as a heuristic
                 parent_window = current_focus

        new_color_info = colorchooser.askcolor(initialcolor=self.crosshair_color, title="Pick Crosshair Color", parent=parent_window)
        if new_color_info and new_color_info[1]: # new_color_info[1] is the hex string
            self.set_crosshair_color(new_color_info[1])
            
    def update_negative_state(self):
        """Update UI elements in crosshair dialog based on negative color setting, and redraw crosshair."""
        is_negative = self.crosshair_use_negative.get()
        # Update preview label in the dialog if it exists
        if hasattr(self, 'crosshair_color_preview_label') and self.crosshair_color_preview_label.winfo_exists():
            if is_negative:
                self.crosshair_color_preview_label.config(bg="SystemButtonFace", text="N/A") # Standard inactive bg
            else:
                self.crosshair_color_preview_label.config(bg=self.crosshair_color, text=" ")
        # Any other UI elements in the dialog that depend on this can be updated here.
        self.update_crosshair() # Redraw the actual crosshair on the canvas

    def set_crosshair_color(self, color_hex):
        """Set the crosshair color, update UI, and redraw crosshair."""
        self.crosshair_color = color_hex
        self.crosshair_use_negative.set(False) # Explicitly turn off negative mode
        # Update preview label in the dialog if it exists
        if hasattr(self, 'crosshair_color_preview_label') and self.crosshair_color_preview_label.winfo_exists():
            self.crosshair_color_preview_label.config(bg=self.crosshair_color, text=" ")
        self.update_crosshair() # Redraw the actual crosshair on the canvas

    def pick_bg_color_dialog(self):
        """Open a color picker dialog for the background color."""
        try:
            # Use the imported rgb_to_hex from utils for consistency if available
            # Assuming self.bg_color is always a valid RGB tuple (e.g., (255,255,255))
            initial_color_hex = rgb_to_hex(self.bg_color) # from utils
            
            color_info = colorchooser.askcolor(initialcolor=initial_color_hex, title="Choose Background Color", parent=self.root)
            if color_info and color_info[1]: # color_info[1] is the hex string if a color is chosen
                hex_color_val = color_info[1].lstrip('#')
                # Convert hex to RGB tuple
                r = int(hex_color_val[0:2], 16)
                g = int(hex_color_val[2:4], 16)
                b = int(hex_color_val[4:6], 16)
                self.bg_color = (r, g, b, 255) # Set as RGBA with full opacity
                
                self.update_bg_color_display() # Update the color box in main UI
                self.logger.info(f"Background color set to {self.bg_color} via color dialog")
        except Exception as e:
            self.logger.warning(f"Error picking background color via dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to pick background color: {str(e)}", parent=self.root)

    def show_color_picker_menu(self, event):
        """Show a color picker dialog when right-clicking the reset button."""
        try:
            # Convert current bg_color (RGB tuple) to hex for the color chooser's initial color
            # The utility function rgb_to_hex is imported from utils.
            initial_color_hex = rgb_to_hex(self.bg_color[:3])

            # Open the color chooser dialog
            color_info = colorchooser.askcolor(
                initialcolor=initial_color_hex,
                title="Pick Background Color for Reset Button",
                parent=self.root  # Parent to the main application window
            )

            if color_info and color_info[1]:  # color_info[1] is the hex string if a color is chosen
                hex_color_val = color_info[1].lstrip('#')
                
                # Convert chosen hex color back to an RGB tuple
                r = int(hex_color_val[0:2], 16)
                g = int(hex_color_val[2:4], 16)
                b = int(hex_color_val[4:6], 16)
                
                self.bg_color = (r, g, b, 255) # Set as RGBA with full opacity
                
                self.update_bg_color_display()  # Update the color box in the main UI
                
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info(f"Background color set to {self.bg_color} via right-click on reset button.")
            # If color_info is None (dialog cancelled), do nothing.

        except Exception as e:
            if hasattr(self, 'logger') and self.logger:
                self.logger.warning(f"Error in show_color_picker_menu (right-click reset bg color): {str(e)}")
            messagebox.showerror(
                "Color Picker Error",
                f"Failed to pick background color: {str(e)}",
                parent=self.root
            )

    def bg_color_settings_dialog(self):
        """Show dialog for background color box settings."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Background Color Box Settings")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Position options
        position_frame = ttk.LabelFrame(main_frame, text="Box Position", padding="10")
        position_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Use self.bg_color_box_position which is loaded from settings or defaults to "top"
        position_var = tk.StringVar(value=self.bg_color_box_position) 

        def on_position_change():
            new_pos = position_var.get()
            if new_pos != self.bg_color_box_position:
                self.bg_color_box_position = new_pos
                # Ensure color box is enabled before adjusting frames
                if not self.bg_color_toggle_var.get():
                    self.bg_color_toggle_var.set(True)
                self.adjust_frames() # Re-layout the main UI
                if self.current_image: # Refresh canvas if image is loaded
                    self.show_image() 
                # Save to user_settings.ini
                try:
                    # Read existing settings first to preserve other settings
                    settings = {}
                    if os.path.exists("user_settings.ini"):
                        with open("user_settings.ini", "r") as f_read:
                            for line in f_read:
                                if "=" in line:
                                    key, value = line.split("=", 1)
                                    settings[key.strip()] = value.strip()
                    
                    settings["BG_COLOR_BOX_POSITION"] = self.bg_color_box_position
                    
                    with open("user_settings.ini", "w") as f_write:
                        for key, value in settings.items():
                            f_write.write(f"{key}={value}\n")
                    self.logger.info(f"Saved BG_COLOR_BOX_POSITION={self.bg_color_box_position} to user_settings.ini")
                except Exception as e_save:
                    self.logger.error(f"Could not save BG_COLOR_BOX_POSITION to user_settings.ini: {e_save}")
            if hasattr(dialog, 'preview_canvas'): # Check if preview_canvas exists
                update_layout_preview(dialog.preview_canvas, position_var, hex_var) # Pass canvas and vars

        ttk.Radiobutton(position_frame, text="Top (above image canvas)", variable=position_var, value="top", command=on_position_change).pack(anchor="w")
        ttk.Radiobutton(position_frame, text="Bottom (below image canvas)", variable=position_var, value="bottom", command=on_position_change).pack(anchor="w")

        # Display options
        display_opts_frame = ttk.LabelFrame(main_frame, text="Display Options", padding="10")
        display_opts_frame.pack(fill=tk.X, pady=(0,10))
        
        hex_var = tk.BooleanVar(value=self.show_hex_in_label)
        def on_hex_toggle():
            self.show_hex_in_label = hex_var.get()
            self.update_bg_color_display() # Update the actual color box
            if hasattr(dialog, 'preview_canvas'): # Check if preview_canvas exists
                 update_layout_preview(dialog.preview_canvas, position_var, hex_var) # Update the preview in this dialog

        ttk.Checkbutton(display_opts_frame, text="Show Hex Color Value (e.g., #RRGGBB)", variable=hex_var, command=on_hex_toggle).pack(anchor="w")

        # Preview
        preview_section_frame = ttk.LabelFrame(main_frame, text="Layout Preview", padding="10")
        preview_section_frame.pack(fill=tk.X, pady=(0,10))
        # Store canvas on dialog to access in callbacks if needed, and pass to update_layout_preview
        dialog.preview_canvas = tk.Canvas(preview_section_frame, width=200, height=100, bg="lightgrey") 
        dialog.preview_canvas.pack(pady=5)

        def update_layout_preview(canvas_widget, pos_var, h_var):
            canvas_widget.delete("all")
            pos = pos_var.get()
            show_h = h_var.get()
            
            canvas_widget.create_rectangle(20, 20, 180, 80, fill="white", outline="black")
            canvas_widget.create_text(100, 50, text="Image Canvas")
            color_box_text = "HEX: #123456" if show_h else "Background Color"
            if pos == "top":
                canvas_widget.create_rectangle(20, 5, 180, 18, fill="magenta", outline="black")
                canvas_widget.create_text(100, 11, text=color_box_text, fill="white", font=("Arial", 7))
            else: # bottom
                canvas_widget.create_rectangle(20, 82, 180, 95, fill="magenta", outline="black")
                canvas_widget.create_text(100, 88, text=color_box_text, fill="white", font=("Arial", 7))
        
        update_layout_preview(dialog.preview_canvas, position_var, hex_var) # Initial draw

        ttk.Button(main_frame, text="OK", command=dialog.destroy).pack(pady=(10,0))

        dialog.update_idletasks()
        x_pos = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_reqwidth() // 2)
        y_pos = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_reqheight() // 2)
        dialog.geometry(f"+{x_pos}+{y_pos}")
        dialog.focus_force()

    def correct_coordinates(self, event):
        """Convert event coordinates to image coordinates considering zoom and pan.
           Returns (img_x, img_y) or (None, None) if coordinates cannot be determined."""
        if not self.current_image:
            self.logger.debug("correct_coordinates: No current_image.")
            return None, None
        if not self.tk_image:
            # This state (current_image exists but tk_image doesn't) should ideally not happen
            # if an image is properly shown. If it does, we cannot determine image coordinates.
            self.logger.debug("correct_coordinates: No tk_image available.")
            return None, None

        try:
            # Get canvas coordinates from the event
            x_canvas = self.canvas.canvasx(event.x)
            y_canvas = self.canvas.canvasy(event.y)
        except Exception as e: # Catch broad errors, e.g., if event object is malformed or canvas is destroyed
            self.logger.warning(f"correct_coordinates: Error getting canvas coordinates from event: {e}")
            return None, None

        try:
            tk_w = self.tk_image.width()
            tk_h = self.tk_image.height()
            if tk_w == 0 or tk_h == 0:
                self.logger.warning(f"correct_coordinates: tk_image has zero dimension: {tk_w}x{tk_h}.")
                return None, None # Cannot reliably scale if displayed image has no size
        except tk.TclError:
            # This can happen if the tk_image is destroyed or becomes invalid between operations
            self.logger.warning("correct_coordinates: TclError getting tk_image dimensions.")
            return None, None # tk_image is invalid

        # Top-left corner of the displayed tk_image on the canvas
        img_left_on_canvas = self.image_x - (tk_w // 2)
        img_top_on_canvas = self.image_y - (tk_h // 2)

        # Click position relative to the top-left of the tk_image (in tk_image's scaled pixels)
        rel_x_on_tk_image = x_canvas - img_left_on_canvas
        rel_y_on_tk_image = y_canvas - img_top_on_canvas

        # Scale these relative coordinates to the original image's coordinate system
        # Ensure current_image dimensions are valid before division
        if self.current_image.width == 0 or self.current_image.height == 0:
            self.logger.warning(f"correct_coordinates: current_image has zero dimension: {self.current_image.width}x{self.current_image.height}.")
            return None, None

        orig_x = int(rel_x_on_tk_image * (self.current_image.width / tk_w))
        orig_y = int(rel_y_on_tk_image * (self.current_image.height / tk_h))
        
        # Optional: Add detailed logging for debugging coordinate transformations
        # self.logger.debug(f"correct_coordinates: event=({event.x},{event.y}) -> canvas=({x_canvas},{y_canvas}) -> tk_img_rel=({rel_x_on_tk_image},{rel_y_on_tk_image}) @ zoom={self.zoom_level} -> orig=({orig_x},{orig_y})")
        return orig_x, orig_y

    def rgb_to_hex(self, rgb_tuple):
        """Converts an RGB tuple to a hexadecimal color string."""
        # This is a class method, ensure it's the one used if self.rgb_to_hex is called.
        # The utils.rgb_to_hex is also available via import.
        try:
            # Use only the first three components (RGB) for hex conversion
            return f"#{rgb_tuple[0]:02x}{rgb_tuple[1]:02x}{rgb_tuple[2]:02x}"
        except (IndexError, TypeError) as e:
            self.logger.error(f"Invalid RGB tuple for rgb_to_hex: {rgb_tuple} - {e}")
            return "#000000" # Fallback to black

    def ask_target_size(self):
        # This is one of the methods that appeared duplicated in the original file.
        # Ensuring a single, correct version is restored.
        global TARGET_SIZE
        picker = ResolutionPicker(self.root) # Assuming ResolutionPicker is correctly defined/imported
        picker.withdraw() # Hide initially to prevent flicker
        # Make picker modal to the root window
        picker.transient(self.root)
        picker.grab_set()

        # Center the picker dialog on the screen
        picker.update_idletasks() # Allow picker to calculate its own required size
        width = picker.winfo_width()
        height = picker.winfo_height()

        screen_w = picker.winfo_screenwidth()
        screen_h = picker.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)

        picker.geometry(f"{width}x{height}+{x}+{y}")

        # NOTE: ResolutionPicker should ideally position itself (e.g., center on parent)
        # in its __init__ method before this deiconify call.
        picker.deiconify() # Show it now that it's configured
        self.root.wait_window(picker) # Wait for picker dialog to close

        if picker.result:
            TARGET_SIZE = picker.result
            self.update_preview_mode_menu() # Update preview options if resolutions change
            self.root.update_idletasks()
            current_width = self.root.winfo_width()
            if current_width < 400:
                self.root.geometry(f"400x{self.root.winfo_height()}")
            if self.current_image is not None: # If processing already started
                messagebox.showinfo("Resolution Updated",
                    f"Selected {len(TARGET_SIZE)} resolution(s):\n"
                    + "\n".join(f"{w}x{h}" for w, h in TARGET_SIZE), parent=self.root)
            return True # Indicate success
        else: # Picker was cancelled
             if self.current_image is None and not TARGET_SIZE: # No image loaded AND no target sizes set from before
                 self.logger.info("ask_target_size: Picker cancelled on initial launch with no prior TARGET_SIZE. Aborting.")
                 # Ensuring self.root is still valid before quitting
                 if self.root and self.root.winfo_exists():
                    # self.root.quit() # Old direct quit
                    return False # Indicate abort
             else:
                  self.logger.info("ask_target_size: Picker cancelled, but continuing with existing TARGET_SIZE or loaded image.")
                  if TARGET_SIZE: # Only show warning if there was a previous setting
                    messagebox.showwarning("Resolution Not Changed", "Resolution selection was cancelled. Using previous settings.", parent=self.root)
             return True # Indicate continue even if warning was shown

    def process_image(self, center_x=None, center_y=None):
        """Process the current image with the current settings."""
        if not self.current_image or not TARGET_SIZE:
            self.logger.warning("process_image called with no current_image or no TARGET_SIZE.")
            return False

        img_path = self.image_paths[self.current_index]
        original_filename = os.path.basename(img_path)
        base_original_filename, _ = os.path.splitext(original_filename)
        # --- MODIFIED: Output filename to .bmp ---
        output_filename_bmp = base_original_filename + ".bmp"
        # --- END MODIFICATION ---
        all_resolutions_succeeded = True

        if not hasattr(self, 'output_folder') or not self.output_folder:
            self.logger.error("Output folder is not set before processing image! Defaulting...")
            self.output_folder = os.path.join(get_base_path(), "output_resized", "default_fallback")
            os.makedirs(self.output_folder, exist_ok=True)

        for target_w, target_h in TARGET_SIZE:
            try:
                # Ensure the canvas background is opaque, using the RGB from self.bg_color
                r, g, b, _ = self.bg_color  # Unpack, ignore original alpha for canvas
                opaque_canvas_color = (r, g, b, 255)
                result = Image.new("RGBA", (target_w, target_h), opaque_canvas_color)
                
                current_center_x = center_x if center_x is not None else self.current_image.width // 2
                current_center_y = center_y if center_y is not None else self.current_image.height // 2

                offset_x = target_w // 2 - current_center_x
                offset_y = target_h // 2 - current_center_y

                from_x = max(0, -offset_x)
                from_y = max(0, -offset_y)
                to_x = min(self.current_image.width, target_w - offset_x)
                to_y = min(self.current_image.height, target_h - offset_y)

                if from_x < to_x and from_y < to_y:
                    cropped = self.current_image.crop((from_x, from_y, to_x, to_y))
                    paste_x = max(0, offset_x)
                    paste_y = max(0, offset_y)
                    # --- MODIFIED PASTE LOGIC ---
                    if cropped.mode == 'RGBA':
                        # If the cropped image has an alpha channel, use its alpha band as the mask.
                        result.paste(cropped, (paste_x, paste_y), mask=cropped.split()[3])
                    elif cropped.mode == 'RGB':
                        # If cropped is RGB (no alpha), paste it directly.
                        result.paste(cropped, (paste_x, paste_y))
                    else:
                        # Handle other modes or log a warning
                        self.logger.warning(f"process_image: Cropped image has unexpected mode {cropped.mode}. Pasting without mask.")
                        result.paste(cropped, (paste_x, paste_y))
                    # --- END MODIFIED PASTE LOGIC ---
                else:
                    self.logger.info(f"Skipping paste for {target_w}x{target_h} on {original_filename} due to invalid crop box.")

                resolution_specific_folder = os.path.join(self.output_folder, f"{target_w}x{target_h}")
                os.makedirs(resolution_specific_folder, exist_ok=True)
                # --- MODIFIED: Use BMP filename for output path ---
                output_path = os.path.join(resolution_specific_folder, output_filename_bmp)
                # --- END MODIFICATION ---
                result.save(output_path)
                self.last_output_path = output_path

                self.stats_manager.add_processed_file(output_filename_bmp, [(target_w, target_h)], self.bg_color)

            except Exception as e_proc:
                error_message = f"Error processing {output_filename_bmp} for {target_w}x{target_h}: {e_proc}"
                detailed_traceback = traceback.format_exc()

                # Force logging and output of the traceback
                print("--- PROCESS_IMAGE ERROR ---") # For stdout visibility
                print(error_message)
                print(detailed_traceback)
                print("--- END PROCESS_IMAGE ERROR ---")

                if hasattr(self, 'logger') and self.logger:
                    self.logger.error(error_message)
                    self.logger.error("Traceback from process_image (explicit log):")
                    self.logger.error(detailed_traceback)

                if hasattr(self, 'log_buffer') and self.log_buffer:
                    self.log_buffer.write("--- PROCESS_IMAGE ERROR (BUFFER) ---\n")
                    self.log_buffer.write(error_message + "\n")
                    self.log_buffer.write(detailed_traceback + "\n")
                    self.log_buffer.write("--- END PROCESS_IMAGE ERROR (BUFFER) ---\n")
                all_resolutions_succeeded = False
        
        return all_resolutions_succeeded

    def prompt_open_file_or_folder(self):
        """Shows a dialog to choose whether to open a single file or a folder of images."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Open")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        content_frame = ttk.Frame(dialog, padding="15 5 15 5") 
        content_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(content_frame, text="What would you like to open?", font=("Arial", 11)).pack(pady=(5, 10))

        action_buttons_frame = ttk.Frame(content_frame)
        action_buttons_frame.pack(fill=tk.X, pady=(0,5))

        def handle_choice(choice_type):
            dialog.destroy()
            if choice_type == "file":
                self._open_single_file_action()
            elif choice_type == "folder":
                self._open_image_folder_action()

        img_button = ttk.Button(action_buttons_frame, text="Image File", command=lambda: handle_choice("file"))
        img_button.pack(fill=tk.X, padx=10, pady=2)

        folder_button = ttk.Button(action_buttons_frame, text="Folder of Images", command=lambda: handle_choice("folder"))
        folder_button.pack(fill=tk.X, padx=10, pady=2)

        cancel_frame = ttk.Frame(content_frame)
        cancel_frame.pack(fill=tk.X, pady=(5,0))

        cancel_button = ttk.Button(cancel_frame, text="Cancel", command=dialog.destroy, width=12)
        cancel_button.pack(pady=(5,5))

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        img_button.focus_set()

        dialog.update_idletasks()
        width = dialog.winfo_reqwidth()
        height = dialog.winfo_reqheight()
        
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        main_h = self.root.winfo_height()

        if main_w == 1 and main_h == 1: 
            screen_w = dialog.winfo_screenwidth()
            screen_h = dialog.winfo_screenheight()
            x = (screen_w // 2) - (width // 2)
            y = (screen_h // 2) - (height // 2)
        else:
            x = main_x + (main_w // 2) - (width // 2)
            y = main_y + (main_h // 2) - (height // 2)
        
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        dialog.wait_window() # Wait for the dialog to be closed before returning

    def handle_ctrl_g_grid_toggle(self, event=None): # <<< ADDED new method for Ctrl+G
        self.show_grid_var.set(not self.show_grid_var.get())
        self.toggle_grid()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizerApp(root)
    # Only run mainloop if setup was successful and root window still exists
    if hasattr(app, 'setup_successful') and app.setup_successful and root.winfo_exists():
        root.mainloop()
    elif not (hasattr(app, 'setup_successful') and app.setup_successful):
        # This case handles if app initialization failed catastrophically before setup_successful was even set
        # or if setup_successful is False. The after_idle(root.destroy) should have been called.
        # We add a failsafe print here for debugging, mainloop won't run.
        print("Application setup failed or was aborted. Exiting.")
        if root.winfo_exists(): # If destroy wasn't called or hasn't processed, ensure it does.
            root.destroy()
