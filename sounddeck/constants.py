import os
import sys

APP_NAME = "SoundDeck"
APP_VERSION = "1.1.0-alpha.5"
CONFIG_NAME = "sounddeck_config.json"
SUPPORTED = {
    ".flac", ".wav", ".aiff", ".aif", ".ogg", ".w64", ".rf64",
    ".mp3", ".m4a", ".aac", ".wma", ".opus", ".webm", ".mp4", ".mka", ".caf"
}
CHUNK = 2048
SAMPLE_RATE = 48000
CHANNELS = 2
SEEK_SECONDS = 10

def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = app_dir()
    return os.path.join(base_path, relative_path)

CONFIG_FILE = os.path.join(app_dir(), CONFIG_NAME)
