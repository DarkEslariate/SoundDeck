import json
import os
import shutil
from .constants import CONFIG_FILE

DEFAULT_CONFIG = {
    "folders": [],
    "volume": 1.0,
    "mic_volume": 1.0,
    "monitor_volume": 1.0,
    "monitor_device": None,
    "mic_device": "none",
    "playlists": {},
    "favorites": [],
    "tags": {},
    "sound_settings": {},
    "recent": [],
    "grid_pins": [],
    "hotkeys": {},
    "autoplay": True,
    "loop_song": False,
    "loop_playlist": False,
    "mic_passthrough": False,
    "monitor_sound": True,
    "monitor_mic": False,
    "allow_overlap": True,
    "normalize_audio": False,
    "master_limiter": True,
    "overlap_limit": 8,
    "global_hotkeys": False,
    "theme": "dark"
}

class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            self.save()
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update(loaded)
            for key, value in DEFAULT_CONFIG.items():
                if key not in self.data:
                    self.data[key] = value
            if not isinstance(self.data.get("folders"), list):
                self.data["folders"] = []
            if not isinstance(self.data.get("playlists"), dict):
                self.data["playlists"] = {}
            if not isinstance(self.data.get("favorites"), list):
                self.data["favorites"] = []
            if not isinstance(self.data.get("tags"), dict):
                self.data["tags"] = {}
            if not isinstance(self.data.get("sound_settings"), dict):
                self.data["sound_settings"] = {}
            if not isinstance(self.data.get("recent"), list):
                self.data["recent"] = []
            if not isinstance(self.data.get("grid_pins"), list):
                self.data["grid_pins"] = []
            if not isinstance(self.data.get("hotkeys"), dict):
                self.data["hotkeys"] = {}
            if str(self.data.get("theme", "dark")).lower() not in ("dark", "light"):
                self.data["theme"] = "dark"
        except Exception:
            self.save()

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def add_recent(self, path):
        recent = [p for p in self.data.get("recent", []) if p != path]
        recent.insert(0, path)
        self.data["recent"] = recent[:50]
        self.save()

    def sound_settings(self, path):
        store = self.data.setdefault("sound_settings", {})
        item = store.setdefault(path, {})
        item.setdefault("volume", 1.0)
        item.setdefault("loop", False)
        item.setdefault("fade_in_ms", 0)
        item.setdefault("fade_out_ms", 0)
        item.setdefault("trim_start_ms", 0)
        item.setdefault("trim_end_ms", 0)
        return item

    def export_to(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def import_from(self, path):
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            self.data.update(loaded)
            self.save()

    def backup_to(self, path):
        shutil.copy2(CONFIG_FILE, path)
