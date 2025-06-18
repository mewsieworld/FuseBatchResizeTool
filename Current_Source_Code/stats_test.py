import tkinter as tk
from tkinter import ttk

def create_stats_window():
    root = tk.Tk()
    root.title("Test Statistics Window")
    
    # Create main frame
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create paned window for split view
    paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True)
    
    # Create left frame for main stats
    left_frame = ttk.Frame(paned)
    left_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create right frame for folders
    right_frame = ttk.Frame(paned)
    right_frame.pack(fill=tk.BOTH, expand=True)
    
    # Add frames to paned window
    paned.add(left_frame, weight=2)
    paned.add(right_frame, weight=1)
    
    # Add content to frames
    ttk.Label(left_frame, text="Left Frame Content").pack(pady=20)
    ttk.Label(right_frame, text="Right Frame Content").pack(pady=20)
    
    # Run the main loop
    root.mainloop()

if __name__ == "__main__":
    create_stats_window() 