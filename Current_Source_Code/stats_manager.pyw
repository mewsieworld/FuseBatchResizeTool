import json
import os
from datetime import datetime, timedelta
from collections import Counter
import time

class StatsManager:
    def __init__(self):
        self.stats_file = os.path.join(os.path.dirname(__file__), "app_statistics.json")
        self.current_session_start = time.time()
        self.current_session_files = 0
        self.load_stats()

    def load_stats(self):
        default_stats = {
            "total_files_processed": 0,
            "total_time_spent": 0,  # in seconds
            "last_access": None,
            "session_count": 0,
            "background_colors": [],  # list of hex codes
            "resolutions_used": [],  # list of "WxH" strings
            "estimated_time_saved": 0,  # in seconds
            "last_file_processed": None
        }

        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    self.stats = json.load(f)
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
        
        self.save_stats()

    def end_session(self):
        # Update total time spent
        session_duration = time.time() - self.current_session_start
        self.stats["total_time_spent"] += session_duration
        self.save_stats()

    def get_top_colors(self, n=5):
        counter = Counter(self.stats["background_colors"])
        return counter.most_common(n)

    def get_top_resolutions(self, n=5):
        counter = Counter(self.stats["resolutions_used"])
        return counter.most_common(n)

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
        
        # Format last access
        if self.stats["last_access"]:
            last_access = datetime.fromisoformat(self.stats["last_access"])
            stats["last_access"] = last_access.strftime("%Y-%m-%d %H:%M:%S")
        
        # Format last file
        if self.stats["last_file_processed"]:
            last_file = self.stats["last_file_processed"]
            timestamp = datetime.fromisoformat(last_file["timestamp"])
            stats["last_file"] = {
                "name": last_file["name"],
                "time": timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Get top colors and resolutions
        stats["top_colors"] = self.get_top_colors()
        stats["top_resolutions"] = self.get_top_resolutions()
        
        # Add other basic stats
        stats["total_files"] = self.stats["total_files_processed"]
        stats["session_count"] = self.stats["session_count"]
        stats["current_session_files"] = self.current_session_files
        
        return stats 