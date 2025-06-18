import json
import os
from datetime import datetime, timedelta
from collections import Counter
import time
import sys

class StatsManager:
    def __init__(self):
        self.stats_file = self.get_stats_path()
        self.current_session_start = time.time()
        self.current_session_files = 0
        self.load_stats()

    def get_stats_path(self):
        if getattr(sys, 'frozen', False):
            # Running as a PyInstaller bundle
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running as a script
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "app_statistics.json")

    def load_stats(self):
        default_stats = {
            "total_files_processed": 0,
            "total_time_spent": 0,  # in seconds
            "last_access": None,
            "session_count": 0,
            "background_colors": [],  # list of hex codes
            "resolutions_used": [],  # list of "WxH" strings
            "estimated_time_saved": 0,  # in seconds
            "last_file_processed": None,
            # New persistent stats
            "largest_batch": 0,
            "file_types": {},  # Dictionary to store file type counts
            "pixels_processed": 0,
            "pixels_by_resolution": {},  # Dictionary to store pixels by resolution
            "folders_extracted": [],
            "longest_session": 0  # in seconds
        }

        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    self.stats = json.load(f)
                    # Ensure all required keys exist
                    for key, default_value in default_stats.items():
                        if key not in self.stats:
                            self.stats[key] = default_value
            else:
                self.stats = default_stats
        except Exception as e:
            print(f"Error loading stats: {e}")
            self.stats = default_stats

        # Update session count and last access
        self.stats["session_count"] += 1
        self.stats["last_access"] = datetime.now().isoformat()
        self.save_stats()

    def save_stats(self):
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")

    def add_processed_file(self, filename, resolutions, bg_color):
        # Update total files
        self.stats["total_files_processed"] += 1
        self.current_session_files += 1
        
        # Update last file
        self.stats["last_file_processed"] = {
            "name": filename,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update background colors (store as hex)
        hex_color = "#{:02x}{:02x}{:02x}".format(*bg_color)
        self.stats["background_colors"].append(hex_color)
        
        # Update resolutions
        for w, h in resolutions:
            self.stats["resolutions_used"].append(f"{w}x{h}")
        
        # Update estimated time saved (2.33 minutes per 5 images)
        time_saved = (2.33 * 60) * (1/5)  # Convert to seconds per image
        self.stats["estimated_time_saved"] += time_saved
        
        # File type tracking
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        if ext:
            self.stats["file_types"].setdefault(ext, 0)
            self.stats["file_types"][ext] += 1
        
        # Pixels processed and by resolution
        for w, h in resolutions:
            pixels = w * h
            self.stats["pixels_processed"] += pixels
            res_str = f"{w}x{h}"
            self.stats["pixels_by_resolution"].setdefault(res_str, 0)
            self.stats["pixels_by_resolution"][res_str] += pixels
        
        # Folders extracted
        folder = os.path.dirname(filename)
        if folder and folder not in self.stats["folders_extracted"]:
            self.stats["folders_extracted"].append(folder)
        
        self.save_stats()

    def end_session(self):
        # Update total time spent
        session_duration = time.time() - self.current_session_start
        self.stats["total_time_spent"] += session_duration
        
        # Update largest batch if needed
        if self.current_session_files > self.stats.get("largest_batch", 0):
            self.stats["largest_batch"] = self.current_session_files
            
        # Update longest session if needed
        if session_duration > self.stats.get("longest_session", 0):
            self.stats["longest_session"] = session_duration
        
        self.save_stats()

    def get_top_colors(self, n=5):
        counter = Counter(self.stats["background_colors"])
        return counter.most_common(n)

    def get_top_resolutions(self, n=5):
        counter = Counter(self.stats["resolutions_used"])
        return counter.most_common(n)

    def get_top_file_types(self, n=5):
        return Counter(self.stats["file_types"]).most_common(n)

    def get_total_pixels(self):
        return self.stats["pixels_processed"]

    def get_pixels_by_resolution(self):
        return self.stats["pixels_by_resolution"]

    def get_folders_extracted(self):
        return self.stats["folders_extracted"]

    def format_time_hms(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:  # Include seconds if it's the only non-zero value
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
        return " ".join(parts)

    def get_formatted_stats(self):
        stats = {}
        
        # Format time spent
        stats["total_time"] = self.format_time_hms(self.stats["total_time_spent"])
        
        # Format estimated time saved
        stats["time_saved"] = self.format_time_hms(self.stats["estimated_time_saved"])
        
        # Format longest session
        stats["longest_session"] = self.format_time_hms(self.stats.get("longest_session", 0))
        
        # Format last access
        if self.stats["last_access"]:
            last_access = datetime.fromisoformat(self.stats["last_access"])
            stats["last_access"] = last_access.strftime("%Y-%m-%d %H:%M:%S")
        
        # Format last file with path shortening
        if self.stats["last_file_processed"]:
            last_file = self.stats["last_file_processed"]
            timestamp = datetime.fromisoformat(last_file["timestamp"])
            # Shorten the file path if it's too long
            file_path = last_file["name"]
            if len(file_path) > 50:
                # Keep first 20 chars and last 20 chars, with ... in between
                file_path = f"{file_path[:20]}...{file_path[-20:]}"
            stats["last_file"] = {
                "name": file_path,
                "time": timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Get top colors and resolutions
        stats["top_colors"] = self.get_top_colors()
        stats["top_resolutions"] = self.get_top_resolutions()
        
        # Add other basic stats
        stats["total_files"] = self.stats["total_files_processed"]
        stats["session_count"] = self.stats["session_count"]
        stats["current_session_files"] = self.current_session_files
        
        stats["largest_batch"] = self.stats.get("largest_batch", 0)
        stats["top_file_types"] = self.get_top_file_types(10)
        stats["total_pixels"] = self.get_total_pixels()
        stats["pixels_by_resolution"] = self.get_pixels_by_resolution()
        
        # Format folders extracted with wrapping and labels
        max_folder_length = 50  # Maximum characters per line
        wrapped_folders = []
        for i, folder in enumerate(self.get_folders_extracted(), 1):
            # Shorten the folder path if it's too long
            if len(folder) > max_folder_length:
                # Keep first 20 chars and last 20 chars, with ... in between
                shortened_path = f"{folder[:20]}...{folder[-20:]}"
                wrapped_folders.append(f"Folder {i}: {shortened_path}")
            else:
                wrapped_folders.append(f"Folder {i}: {folder}")
        stats["folders_extracted"] = wrapped_folders
        
        return stats 