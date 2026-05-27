import os
from pathlib import Path
from .constants import SUPPORTED

class Library:
    def __init__(self, cfg):
        self.cfg = cfg
        self.files = []

    def scan(self):
        found = []
        folders = []
        for folder in self.cfg.data.get("folders", []):
            if folder not in folders:
                folders.append(folder)
            if not os.path.exists(folder):
                continue
            for root, _, names in os.walk(folder):
                for name in names:
                    if Path(name).suffix.lower() in SUPPORTED:
                        found.append(os.path.join(root, name))
        self.cfg.data["folders"] = folders
        self.files = sorted(set(found), key=lambda p: Path(p).name.lower())
        self.cfg.save()
        return self.files

    def search(self, query):
        query = query.lower().strip()
        tags = self.cfg.data.get("tags", {})
        if not query:
            return self.files[:]
        result = []
        for path in self.files:
            text = f"{Path(path).name} {Path(path).parent} {' '.join(tags.get(path, []))}".lower()
            if query in text:
                result.append(path)
        return result

    def display_name(self, path):
        fav = "★ " if path in self.cfg.data.get("favorites", []) else ""
        return fav + Path(path).name
