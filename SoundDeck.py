import os
import sys
import json
import subprocess
import threading
from collections import deque
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox

import numpy as np
import sounddevice as sd
import soundfile as sf


APP_NAME = "SoundDeck"
APP_VERSION = "1.0.1"
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
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = app_dir()
    return os.path.join(base_path, relative_path)


CONFIG_FILE = os.path.join(app_dir(), CONFIG_NAME)


THEME_MODE = "dark"

THEME_BG = "#0c1a2b"
THEME_PANEL = "#000000"
THEME_PANEL_2 = "#111111"
THEME_CARD = "#1b1b1b"
THEME_BLUE = "#1e88ff"
THEME_BLUE_2 = "#58a6ff"
THEME_TEXT = "#e7f1ff"
THEME_BG_TEXT = "#e7f1ff"
THEME_MUTED = "#9fb4cf"
THEME_BORDER = "#2f65a0"
THEME_GOOD = "#42d392"
THEME_BAD = "#ff5c7a"
THEME_SELECT = "#1e88ff"


def set_theme_mode(mode):
    global THEME_MODE
    global THEME_BG, THEME_PANEL, THEME_PANEL_2, THEME_CARD
    global THEME_BLUE, THEME_BLUE_2, THEME_TEXT, THEME_BG_TEXT
    global THEME_MUTED, THEME_BORDER, THEME_GOOD, THEME_BAD, THEME_SELECT

    THEME_MODE = "light" if str(mode).lower() == "light" else "dark"


    THEME_BLUE = "#1e88ff"
    THEME_BLUE_2 = "#58a6ff"
    THEME_GOOD = "#42d392"
    THEME_BAD = "#ff5c7a"
    THEME_SELECT = "#1e88ff"

    if THEME_MODE == "light":

        THEME_BG = "#aacfff"
        THEME_PANEL = "#ffffff"
        THEME_PANEL_2 = "#f5f9ff"
        THEME_CARD = "#e8f1fc"
        THEME_TEXT = "#142033"
        THEME_BG_TEXT = "#142033"
        THEME_MUTED = "#5e7188"
        THEME_BORDER = "#8cb8ea"
    else:

        THEME_BG = "#0c1a2b"
        THEME_PANEL = "#000000"
        THEME_PANEL_2 = "#111111"
        THEME_CARD = "#1b1b1b"
        THEME_TEXT = "#e7f1ff"
        THEME_BG_TEXT = "#e7f1ff"
        THEME_MUTED = "#9fb4cf"
        THEME_BORDER = "#2f65a0"


def apply_theme(root, mode="dark"):
    set_theme_mode(mode)

    root.configure(bg=THEME_BG)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", font=("Segoe UI", 10))

    style.configure("TFrame", background=THEME_BG)
    style.configure("Panel.TFrame", background=THEME_PANEL)

    style.configure("TLabel", background=THEME_PANEL, foreground=THEME_TEXT)
    style.configure("Panel.TLabel", background=THEME_PANEL, foreground=THEME_TEXT)
    style.configure("Muted.TLabel", background=THEME_PANEL, foreground=THEME_MUTED)

    style.configure(
        "TLabelframe",
        background=THEME_PANEL,
        foreground=THEME_TEXT,
        bordercolor=THEME_BORDER,
    )
    style.configure(
        "TLabelframe.Label",
        background=THEME_BG,
        foreground=THEME_BLUE_2,
        font=("Segoe UI", 10, "bold"),
    )

    style.configure(
        "TButton",
        background=THEME_PANEL_2,
        foreground=THEME_TEXT,
        borderwidth=0,
        focusthickness=0,
        padding=(10, 5),
    )
    style.map(
        "TButton",
        background=[("active", THEME_CARD), ("pressed", THEME_BLUE)],
        foreground=[("active", THEME_TEXT), ("pressed", "#ffffff")],
    )

    style.configure(
        "TCheckbutton",
        background=THEME_PANEL,
        foreground=THEME_TEXT,
        focuscolor=THEME_PANEL,
        padding=(4, 2),
    )
    style.map(
        "TCheckbutton",
        background=[("active", THEME_PANEL)],
        foreground=[("active", THEME_BLUE_2)],
    )

    style.configure(
        "TEntry",
        fieldbackground=THEME_PANEL_2,
        background=THEME_PANEL_2,
        foreground=THEME_TEXT,
        insertcolor=THEME_TEXT,
        bordercolor=THEME_BORDER,
        lightcolor=THEME_BORDER,
        darkcolor=THEME_BORDER,
    )

    style.configure(
        "TCombobox",
        fieldbackground=THEME_PANEL_2,
        background=THEME_PANEL_2,
        foreground=THEME_TEXT,
        arrowcolor=THEME_BLUE_2,
        bordercolor=THEME_BORDER,
        lightcolor=THEME_BORDER,
        darkcolor=THEME_BORDER,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", THEME_PANEL_2)],
        foreground=[("readonly", THEME_TEXT)],
        selectbackground=[("readonly", THEME_PANEL_2)],
        selectforeground=[("readonly", THEME_TEXT)],
    )

    style.configure(
        "Horizontal.TScale",
        background=THEME_PANEL,
        troughcolor=THEME_PANEL_2,
        bordercolor=THEME_PANEL,
        lightcolor=THEME_BLUE,
        darkcolor=THEME_BLUE,
    )


def style_listbox(widget):
    widget.configure(
        bg=THEME_PANEL,
        fg=THEME_TEXT,
        selectbackground=THEME_SELECT,
        selectforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=THEME_BORDER,
        highlightcolor=THEME_BLUE,
        activestyle="none",
        font=("Segoe UI", 10),
    )


def refresh_manual_widget_theme(app):
    for widget_name in ("library_list", "queue_list", "playlist_tracks"):
        widget = getattr(app, widget_name, None)
        if widget:
            style_listbox(widget)

    relay_status = getattr(app, "relay_status", None)
    if relay_status:
        relay_status.configure(bg=THEME_PANEL)

    root = getattr(app, "root", None)
    if root:
        root.configure(bg=THEME_BG)


def find_bundled_ffmpeg():
    possible_dirs = [
        os.path.join(app_dir(), "ffmpeg"),
        resource_path("ffmpeg"),
        os.path.join(app_dir(), "_internal", "ffmpeg"),
    ]

    for folder in possible_dirs:
        ffmpeg_path = os.path.join(folder, "ffmpeg.exe")
        ffprobe_path = os.path.join(folder, "ffprobe.exe")
        if os.path.exists(ffmpeg_path):
            return folder, ffmpeg_path, ffprobe_path

    return None, None, None


FFMPEG_FOLDER, FFMPEG_EXE, FFPROBE_EXE = find_bundled_ffmpeg()

if FFMPEG_FOLDER:
    os.environ["PATH"] = FFMPEG_FOLDER + os.pathsep + os.environ.get("PATH", "")


def subprocess_flags():
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


def output_channels_supported(device):
    for channels in (2, 1):
        try:
            sd.check_output_settings(
                device=device,
                samplerate=SAMPLE_RATE,
                channels=channels,
                dtype="float32",
            )
            return channels
        except Exception:
            pass
    return None


def input_channels_supported(device):
    try:
        sd.check_input_settings(
            device=device,
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        return 1
    except Exception:
        return None


def is_vb_cable_playback_name(name):
    """
    VB-Cable playback/output endpoint is usually:
    CABLE Input (VB-Audio Virtual Cable)

    Discord/OBS should use the recording/input endpoint:
    CABLE Output
    """
    n = name.lower()

    if "cable input" in n:
        return True

    if "vb-audio" in n and "input" in n and "cable" in n:
        return True

    if "vb-audio virtual cable" in n and "input" in n:
        return True

    return False


def find_vb_cable_relay_output():
    try:
        devices = sd.query_devices()
    except Exception:
        return None, None

    candidates = []

    for i, dev in enumerate(devices):
        name = dev.get("name", f"Device {i}")

        if dev.get("max_output_channels", 0) <= 0:
            continue

        if output_channels_supported(i) is None:
            continue

        if is_vb_cable_playback_name(name):
            score = 0 if "cable input" in name.lower() else 1
            candidates.append((score, i, name))

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[0])
    _, idx, name = candidates[0]
    return idx, name


def decode_with_ffmpeg(path):
    if not FFMPEG_EXE or not os.path.exists(FFMPEG_EXE):
        raise RuntimeError(
            "FFmpeg was not found.\n\n"
            "Make sure your built app has:\n"
            "_internal\\ffmpeg\\ffmpeg.exe\n"
            "_internal\\ffmpeg\\ffprobe.exe\n\n"
            f"Detected FFMPEG_EXE:\n{FFMPEG_EXE}"
        )

    cmd = [
        FFMPEG_EXE,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        path,
        "-vn",
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "2",
        "-ar",
        str(SAMPLE_RATE),
        "pipe:1",
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess_flags(),
        )
    except Exception as e:
        raise RuntimeError(f"Could not run ffmpeg.exe:\n{e}")

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            "FFmpeg could not decode this file.\n\n"
            f"File:\n{path}\n\n"
            f"FFmpeg error:\n{err}"
        )

    if not result.stdout:
        raise RuntimeError("FFmpeg decoded no audio data.")

    audio = np.frombuffer(result.stdout, dtype=np.float32)

    if audio.size < 2:
        raise RuntimeError("Decoded audio was empty or invalid.")

    if audio.size % 2 != 0:
        audio = audio[:-1]

    audio = audio.reshape((-1, 2)).copy()
    return np.ascontiguousarray(audio, dtype=np.float32)


def resample_linear(data, src_rate, dst_rate=SAMPLE_RATE):
    if int(src_rate) == int(dst_rate):
        return data.astype(np.float32, copy=False)

    if len(data) == 0:
        return data.astype(np.float32, copy=False)

    ratio = float(dst_rate) / float(src_rate)
    new_len = max(1, int(round(len(data) * ratio)))

    old_x = np.linspace(0.0, 1.0, num=len(data), endpoint=False)
    new_x = np.linspace(0.0, 1.0, num=new_len, endpoint=False)

    out = np.empty((new_len, data.shape[1]), dtype=np.float32)

    for ch in range(data.shape[1]):
        out[:, ch] = np.interp(new_x, old_x, data[:, ch]).astype(np.float32)

    return np.ascontiguousarray(out, dtype=np.float32)


def to_stereo_float32(data):
    data = np.asarray(data, dtype=np.float32)

    if data.ndim == 1:
        data = data.reshape((-1, 1))

    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]

    return np.ascontiguousarray(data, dtype=np.float32)


def decode_audio_file(path):
    if FFMPEG_EXE and os.path.exists(FFMPEG_EXE):
        return decode_with_ffmpeg(path)

    try:
        data, rate = sf.read(path, dtype="float32", always_2d=True)
        data = to_stereo_float32(data)
        return resample_linear(data, rate, SAMPLE_RATE)
    except Exception as e:
        raise RuntimeError(
            "Could not decode this file.\n\n"
            "Bundled FFmpeg was not found, and soundfile fallback failed.\n\n"
            f"Original error:\n{e}"
        )


def fmt_time(seconds):
    seconds = int(max(0, seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def clip_audio(data):
    return np.clip(data, -1.0, 1.0).astype(np.float32, copy=False)


def write_mix_to_outdata(outdata, mix):
    if outdata.shape[1] == 1:
        outdata[:, 0] = np.mean(mix, axis=1)
    else:
        outdata[:, :2] = mix[:, :2]


class Config:
    def __init__(self):
        self.data = {
            "folders": [],
            "volume": 1.0,
            "mic_volume": 1.0,
            "monitor_volume": 1.0,
            "device": None,
            "relay_device": None,
            "monitor_device": None,
            "mic_device": "none",
            "playlists": {},
            "autoplay": True,
            "loop_song": False,
            "loop_playlist": False,
            "mic_passthrough": False,
            "monitor_sound": True,
            "monitor_mic": False,
            "theme": "dark",
        }
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

            if not isinstance(self.data.get("folders"), list):
                self.data["folders"] = []

            if not isinstance(self.data.get("playlists"), dict):
                self.data["playlists"] = {}

            defaults = {
                "volume": 1.0,
                "mic_volume": 1.0,
                "monitor_volume": 1.0,
                "autoplay": True,
                "loop_song": False,
                "loop_playlist": False,
                "mic_passthrough": False,
                "monitor_sound": True,
                "monitor_mic": False,
                "mic_device": "none",
                "relay_device": None,
                "monitor_device": None,
                "device": None,
                "theme": "dark",
            }

            for key, value in defaults.items():
                if self.data.get(key) is None:
                    self.data[key] = value

            if str(self.data.get("theme", "dark")).lower() not in ("dark", "light"):
                self.data["theme"] = "dark"

        except Exception:
            self.save()

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print("Config save error:", e)


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

        if not query:
            return self.files[:]

        return [
            path
            for path in self.files
            if query in Path(path).name.lower()
            or query in str(Path(path).parent).lower()
        ]


class AudioMixer:
    def __init__(self, cfg):
        self.cfg = cfg

        self.file = None
        self.audio = None
        self.frame = 0
        self.total = 0

        self.volume = float(cfg.data.get("volume", 1.0))
        self.mic_volume = float(cfg.data.get("mic_volume", 1.0))
        self.monitor_volume = float(cfg.data.get("monitor_volume", 1.0))

        self.relay_device = None
        self.relay_device_name = None
        self.monitor_device = cfg.data.get("monitor_device")
        self.mic_device = cfg.data.get("mic_device", "none")

        self.mic_passthrough = bool(cfg.data.get("mic_passthrough", False))
        self.monitor_sound = bool(cfg.data.get("monitor_sound", True))
        self.monitor_mic = bool(cfg.data.get("monitor_mic", False))

        self.relay_channels = 2
        self.monitor_channels = 2

        self.playing = False
        self.paused = False

        self.lock = threading.RLock()
        self.generation = 0

        self.relay_stream = None
        self.monitor_stream = None
        self.mic_stream = None

        self.mic_queue = deque()
        self.monitor_queue = deque()
        self.max_queue_chunks = 40

        self.finished_pending = False
        self.relay_missing = False
        self.on_error = None

        self.restart_streams()

    def _sound_gain(self):
        return max(0.0, float(self.volume))

    def _mic_gain(self):
        return max(0.0, float(self.mic_volume))

    def _monitor_gain(self):
        return max(0.0, float(self.monitor_volume))

    def _close_old_streams(self, streams):
        for stream in streams:
            if not stream:
                continue

            try:
                stream.stop()
            except Exception:
                pass

            try:
                stream.close()
            except Exception:
                pass

    def auto_select_relay_device(self):
        idx, name = find_vb_cable_relay_output()

        with self.lock:
            self.relay_device = idx
            self.relay_device_name = name
            self.relay_missing = idx is None

            self.cfg.data["relay_device"] = idx
            self.cfg.data["device"] = idx
            self.cfg.save()

        return idx, name

    def restart_streams(self):
        with self.lock:
            self.generation += 1
            gen = self.generation

            old_streams = [self.relay_stream, self.monitor_stream, self.mic_stream]

            self.relay_stream = None
            self.monitor_stream = None
            self.mic_stream = None

            self.mic_queue.clear()
            self.monitor_queue.clear()

        self._close_old_streams(old_streams)

        relay_device, relay_name = self.auto_select_relay_device()

        if relay_device is not None:
            relay_channels = output_channels_supported(relay_device)

            if relay_channels is None:
                if self.on_error:
                    self.on_error(
                        "VB-Audio Virtual Cable was found, but SoundDeck could not open it.\n\n"
                        "Try restarting your PC, then reopen SoundDeck."
                    )
            else:
                try:
                    relay_stream = sd.OutputStream(
                        samplerate=SAMPLE_RATE,
                        channels=relay_channels,
                        dtype="float32",
                        device=relay_device,
                        blocksize=CHUNK,
                        callback=lambda outdata, frames, time_info, status, g=gen: self._relay_callback(
                            g, outdata, frames, time_info, status
                        ),
                    )
                    relay_stream.start()

                    with self.lock:
                        if gen == self.generation:
                            self.relay_channels = relay_channels
                            self.relay_stream = relay_stream
                        else:
                            self._close_old_streams([relay_stream])

                except Exception as e:
                    if self.on_error:
                        self.on_error(f"VB-Cable relay output failed to start:\n{e}")

        if self.monitor_sound or self.monitor_mic:
            monitor_channels = output_channels_supported(self.monitor_device)

            if monitor_channels is None:
                if self.on_error:
                    self.on_error(
                        "Monitor Output could not start.\n\n"
                        "That device may not support SoundDeck's audio format.\n"
                        "Try System default or your headphones."
                    )
            else:
                try:
                    monitor_stream = sd.OutputStream(
                        samplerate=SAMPLE_RATE,
                        channels=monitor_channels,
                        dtype="float32",
                        device=self.monitor_device,
                        blocksize=CHUNK,
                        callback=lambda outdata, frames, time_info, status, g=gen: self._monitor_callback(
                            g, outdata, frames, time_info, status
                        ),
                    )
                    monitor_stream.start()

                    with self.lock:
                        if gen == self.generation:
                            self.monitor_channels = monitor_channels
                            self.monitor_stream = monitor_stream
                        else:
                            self._close_old_streams([monitor_stream])

                except Exception as e:
                    if self.on_error:
                        self.on_error(f"Monitor Output failed to start:\n{e}")

        if (self.mic_passthrough or self.monitor_mic) and self.mic_device != "none":
            if input_channels_supported(self.mic_device) is None:
                if self.on_error:
                    self.on_error(
                        "Microphone Input could not start.\n\n"
                        "Try System default or your headset microphone."
                    )
            else:
                try:
                    mic_stream = sd.InputStream(
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        dtype="float32",
                        device=self.mic_device,
                        blocksize=CHUNK,
                        callback=lambda indata, frames, time_info, status, g=gen: self._mic_callback(
                            g, indata, frames, time_info, status
                        ),
                    )
                    mic_stream.start()

                    with self.lock:
                        if gen == self.generation:
                            self.mic_stream = mic_stream
                        else:
                            self._close_old_streams([mic_stream])

                except Exception as e:
                    if self.on_error:
                        self.on_error(f"Microphone Input failed to start:\n{e}")

    def close(self):
        with self.lock:
            self.generation += 1
            old_streams = [self.relay_stream, self.monitor_stream, self.mic_stream]

            self.relay_stream = None
            self.monitor_stream = None
            self.mic_stream = None

            self.mic_queue.clear()
            self.monitor_queue.clear()

        self._close_old_streams(old_streams)

    def _mic_callback(self, gen, indata, frames, time_info, status):
        with self.lock:
            if gen != self.generation:
                raise sd.CallbackStop

            data = to_stereo_float32(indata)

            self.mic_queue.append(data)

            while len(self.mic_queue) > self.max_queue_chunks:
                self.mic_queue.popleft()

    def _pop_from_queue(self, queue, frames):
        out = np.zeros((frames, 2), dtype=np.float32)
        filled = 0

        while filled < frames and queue:
            chunk = queue[0]
            need = frames - filled

            if len(chunk) <= need:
                out[filled:filled + len(chunk)] = chunk
                filled += len(chunk)
                queue.popleft()
            else:
                out[filled:] = chunk[:need]
                queue[0] = chunk[need:]
                filled = frames

        return out

    def _sound_chunk(self, frames):
        out = np.zeros((frames, 2), dtype=np.float32)
        ended_now = False

        if not self.playing or self.paused or self.audio is None:
            return out, ended_now

        start = int(self.frame)
        end = min(start + frames, self.total)

        if start >= end:
            self.playing = False
            ended_now = True
            return out, ended_now

        chunk = self.audio[start:end]
        n = len(chunk)

        out[:n] = chunk
        self.frame = end

        if n < frames or self.frame >= self.total:
            self.playing = False
            ended_now = True

        return out, ended_now

    def _relay_callback(self, gen, outdata, frames, time_info, status):
        outdata.fill(0)

        try:
            with self.lock:
                if gen != self.generation:
                    raise sd.CallbackStop

                sound, ended_now = self._sound_chunk(frames)
                mic = self._pop_from_queue(self.mic_queue, frames)

                relay_mix = np.zeros((frames, 2), dtype=np.float32)
                monitor_mix = np.zeros((frames, 2), dtype=np.float32)

                relay_mix += sound * self._sound_gain()

                if self.mic_passthrough:
                    relay_mix += mic * self._mic_gain()

                if self.monitor_sound:
                    monitor_mix += sound * self._sound_gain()

                if self.monitor_mic:
                    monitor_mix += mic * self._mic_gain()

                monitor_mix *= self._monitor_gain()

                if self.monitor_stream:
                    self.monitor_queue.append(clip_audio(monitor_mix))

                    while len(self.monitor_queue) > self.max_queue_chunks:
                        self.monitor_queue.popleft()

                write_mix_to_outdata(outdata, clip_audio(relay_mix))

                if ended_now:
                    self.finished_pending = True

        except sd.CallbackStop:
            raise
        except Exception as e:
            outdata.fill(0)
            if self.on_error:
                self.on_error(f"Audio callback error:\n{e}")

    def _monitor_callback(self, gen, outdata, frames, time_info, status):
        outdata.fill(0)

        try:
            with self.lock:
                if gen != self.generation:
                    raise sd.CallbackStop

                data = self._pop_from_queue(self.monitor_queue, frames)
                write_mix_to_outdata(outdata, clip_audio(data))

        except sd.CallbackStop:
            raise
        except Exception:
            outdata.fill(0)

    def consume_finished(self):
        with self.lock:
            if self.finished_pending:
                self.finished_pending = False
                return True
        return False

    def load(self, path):
        if not os.path.exists(path):
            raise RuntimeError(f"File does not exist:\n{path}")

        samples = decode_audio_file(path)

        with self.lock:
            self.file = path
            self.audio = samples
            self.frame = 0
            self.total = int(len(samples))
            self.playing = False
            self.paused = False
            self.finished_pending = False
            self.monitor_queue.clear()

    def play(self):
        with self.lock:
            if self.audio is None:
                return

            if self.frame >= max(1, self.total - 1):
                self.frame = 0

            self.playing = True
            self.paused = False
            self.finished_pending = False
            self.monitor_queue.clear()

    def stop(self):
        with self.lock:
            self.playing = False
            self.paused = False
            self.frame = 0
            self.finished_pending = False
            self.monitor_queue.clear()

    def pause_toggle(self):
        with self.lock:
            if self.audio is not None:
                self.paused = not self.paused

    def restart(self):
        with self.lock:
            if self.audio is not None:
                self.frame = 0
                self.playing = True
                self.paused = False
                self.finished_pending = False
                self.monitor_queue.clear()

    def seek_seconds(self, seconds):
        with self.lock:
            if self.total <= 0:
                return
            self.frame = max(0, min(self.total - 1, self.frame + int(seconds * SAMPLE_RATE)))
            self.monitor_queue.clear()

    def seek_percent(self, pct):
        with self.lock:
            if self.total <= 0:
                return
            pct = max(0.0, min(1.0, float(pct)))
            self.frame = int(self.total * pct)
            self.monitor_queue.clear()

    def set_volume(self, value):
        with self.lock:
            self.volume = max(0.0, min(2.5, float(value)))
            self.cfg.data["volume"] = self.volume
            self.cfg.save()

    def set_mic_volume(self, value):
        with self.lock:
            self.mic_volume = max(0.0, min(2.5, float(value)))
            self.cfg.data["mic_volume"] = self.mic_volume
            self.cfg.save()

    def set_monitor_volume(self, value):
        with self.lock:
            self.monitor_volume = max(0.0, min(2.5, float(value)))
            self.cfg.data["monitor_volume"] = self.monitor_volume
            self.cfg.save()

    def set_devices(self, monitor_device, mic_device):
        with self.lock:
            self.monitor_device = monitor_device
            self.mic_device = mic_device

            self.cfg.data["monitor_device"] = monitor_device
            self.cfg.data["mic_device"] = mic_device
            self.cfg.save()

        self.restart_streams()

    def set_toggles(self, mic_passthrough, monitor_sound, monitor_mic):
        with self.lock:
            self.mic_passthrough = bool(mic_passthrough)
            self.monitor_sound = bool(monitor_sound)
            self.monitor_mic = bool(monitor_mic)

            self.cfg.data["mic_passthrough"] = self.mic_passthrough
            self.cfg.data["monitor_sound"] = self.monitor_sound
            self.cfg.data["monitor_mic"] = self.monitor_mic
            self.cfg.save()

        self.restart_streams()

    @property
    def pos_seconds(self):
        with self.lock:
            return self.frame / SAMPLE_RATE

    @property
    def dur_seconds(self):
        with self.lock:
            return self.total / SAMPLE_RATE if self.total > 0 else 0

    @property
    def is_playing(self):
        with self.lock:
            return self.playing

    @property
    def is_paused(self):
        with self.lock:
            return self.paused


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = Config()
        self.lib = Library(self.cfg)
        self.mixer = AudioMixer(self.cfg)
        self.mixer.on_error = lambda msg: self.root.after(0, lambda: self.show_audio_error(msg))

        self.visible = []
        self.queue = []
        self.queue_index = -1
        self.dragging_seek = False
        self.vb_error_shown = False

        self.output_devices = {}
        self.input_devices = {}

        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1280x780")
        self.root.minsize(1040, 680)
        apply_theme(self.root, self.cfg.data.get("theme", "dark"))

        self.build_ui()
        self.refresh_devices()
        self.refresh_library()
        self.refresh_playlists()
        self.tick()

    def build_ui(self):
        self.root.columnconfigure(0, weight=2)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=1)

        top = ttk.Frame(self.root, style="Panel.TFrame")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)

        ttk.Button(top, text="Add Folder", command=self.add_folder).pack(side="left")
        ttk.Button(top, text="Remove Folder", command=self.remove_folder).pack(side="left", padx=4)
        ttk.Button(top, text="Scan", command=self.refresh_library).pack(side="left", padx=(0, 12))
        ttk.Button(top, text="Refresh Devices", command=self.refresh_devices).pack(side="left", padx=4)
        ttk.Button(top, text="FFmpeg Check", command=self.ffmpeg_check).pack(side="left", padx=4)

        ttk.Label(top, text="Theme:", style="Panel.TLabel").pack(side="left", padx=(12, 4))
        self.theme_var = tk.StringVar(
            value="Light" if self.cfg.data.get("theme", "dark") == "light" else "Dark"
        )
        self.theme_box = ttk.Combobox(
            top,
            textvariable=self.theme_var,
            state="readonly",
            width=8,
            values=["Dark", "Light"],
        )
        self.theme_box.pack(side="left")
        self.theme_box.bind("<<ComboboxSelected>>", self.change_theme)

        self.setup_tip = ttk.Label(
            top,
            text="Relay is automatic. SoundDeck sends to VB-Cable; Discord/OBS should use CABLE Output as mic.",
            style="Panel.TLabel",
        )
        self.setup_tip.pack(side="left", padx=12)

        routing = ttk.LabelFrame(self.root, text="Routing")
        routing.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6))
        routing.columnconfigure(1, weight=1)
        routing.columnconfigure(3, weight=1)
        routing.columnconfigure(5, weight=1)

        ttk.Label(routing, text="Auto Relay:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.relay_status = tk.Label(
            routing,
            text="Checking VB-Cable...",
            anchor="w",
            bg=THEME_PANEL,
            fg=THEME_MUTED,
            font=("Segoe UI", 10, "bold"),
        )
        self.relay_status.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(routing, text="Microphone Input:").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        self.mic_var = tk.StringVar()
        self.mic_box = ttk.Combobox(routing, textvariable=self.mic_var, state="readonly", width=34)
        self.mic_box.grid(row=0, column=3, sticky="ew", padx=4, pady=4)
        self.mic_box.bind("<<ComboboxSelected>>", self.apply_selected_devices)

        ttk.Label(routing, text="Monitor Output:").grid(row=0, column=4, sticky="w", padx=6, pady=4)
        self.monitor_var = tk.StringVar()
        self.monitor_box = ttk.Combobox(routing, textvariable=self.monitor_var, state="readonly", width=34)
        self.monitor_box.grid(row=0, column=5, sticky="ew", padx=4, pady=4)
        self.monitor_box.bind("<<ComboboxSelected>>", self.apply_selected_devices)

        self.mic_passthrough_var = tk.BooleanVar(value=bool(self.cfg.data.get("mic_passthrough", False)))
        ttk.Checkbutton(
            routing,
            text="Send mic to apps",
            variable=self.mic_passthrough_var,
            command=self.save_routing_options,
        ).grid(row=1, column=0, sticky="w", padx=6, pady=4)

        self.monitor_sound_var = tk.BooleanVar(value=bool(self.cfg.data.get("monitor_sound", True)))
        ttk.Checkbutton(
            routing,
            text="Hear soundboard",
            variable=self.monitor_sound_var,
            command=self.save_routing_options,
        ).grid(row=1, column=1, sticky="w", padx=4, pady=4)

        self.monitor_mic_var = tk.BooleanVar(value=bool(self.cfg.data.get("monitor_mic", False)))
        ttk.Checkbutton(
            routing,
            text="Hear yourself",
            variable=self.monitor_mic_var,
            command=self.save_routing_options,
        ).grid(row=1, column=2, sticky="w", padx=6, pady=4)

        ttk.Label(routing, text="Sound Vol").grid(row=1, column=3, sticky="e", padx=4)
        self.volume_slider = ttk.Scale(routing, from_=0, to=2.5, orient="horizontal", command=self.set_volume)
        self.volume_slider.set(float(self.cfg.data.get("volume", 1.0)))
        self.volume_slider.grid(row=1, column=4, sticky="ew", padx=4)
        self.volume_label = ttk.Label(routing, text=f"{int(float(self.cfg.data.get('volume', 1.0)) * 100)}%")
        self.volume_label.grid(row=1, column=5, sticky="w", padx=4)

        ttk.Label(routing, text="Mic Vol").grid(row=2, column=3, sticky="e", padx=4)
        self.mic_volume_slider = ttk.Scale(routing, from_=0, to=2.5, orient="horizontal", command=self.set_mic_volume)
        self.mic_volume_slider.set(float(self.cfg.data.get("mic_volume", 1.0)))
        self.mic_volume_slider.grid(row=2, column=4, sticky="ew", padx=4)
        self.mic_volume_label = ttk.Label(
            routing,
            text=f"{int(float(self.cfg.data.get('mic_volume', 1.0)) * 100)}%",
        )
        self.mic_volume_label.grid(row=2, column=5, sticky="w", padx=4)

        ttk.Label(routing, text="Monitor Vol").grid(row=2, column=0, sticky="w", padx=6)
        self.monitor_volume_slider = ttk.Scale(
            routing,
            from_=0,
            to=2.5,
            orient="horizontal",
            command=self.set_monitor_volume,
        )
        self.monitor_volume_slider.set(float(self.cfg.data.get("monitor_volume", 1.0)))
        self.monitor_volume_slider.grid(row=2, column=1, sticky="ew", padx=4)
        self.monitor_volume_label = ttk.Label(
            routing,
            text=f"{int(float(self.cfg.data.get('monitor_volume', 1.0)) * 100)}%",
        )
        self.monitor_volume_label.grid(row=2, column=2, sticky="w", padx=4)

        left = ttk.Frame(self.root, style="Panel.TFrame")
        left.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Library").grid(row=0, column=0, sticky="w")

        self.search_entry = ttk.Entry(left)
        self.search_entry.grid(row=1, column=0, sticky="ew", pady=4)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list_only())

        self.library_list = tk.Listbox(left, activestyle="none")
        style_listbox(self.library_list)
        self.library_list.grid(row=2, column=0, sticky="nsew")
        self.library_list.bind("<Double-1>", self.play_selected_file)
        self.library_list.bind("<Button-3>", self.library_right_click)

        right = ttk.Frame(self.root, style="Panel.TFrame")
        right.grid(row=2, column=1, sticky="nsew", padx=8, pady=6)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(5, weight=1)

        ttk.Label(right, text="Queue").grid(row=0, column=0, sticky="w")

        self.queue_list = tk.Listbox(right, height=9, activestyle="none")
        style_listbox(self.queue_list)
        self.queue_list.grid(row=1, column=0, sticky="nsew")
        self.queue_list.bind("<Double-1>", self.play_queue_selected)

        q_buttons = ttk.Frame(right)
        q_buttons.grid(row=2, column=0, sticky="ew", pady=4)

        ttk.Button(q_buttons, text="Add Selected", command=self.add_selected_to_queue).pack(side="left")
        ttk.Button(q_buttons, text="Remove Selected", command=self.remove_selected_queue).pack(side="left", padx=4)
        ttk.Button(q_buttons, text="Clear Queue", command=self.clear_queue).pack(side="left")

        ttk.Label(right, text="Playlists").grid(row=3, column=0, sticky="w", pady=(12, 0))

        playlist_top = ttk.Frame(right)
        playlist_top.grid(row=4, column=0, sticky="ew", pady=4)

        self.playlist_var = tk.StringVar()
        self.playlist_box = ttk.Combobox(playlist_top, textvariable=self.playlist_var, state="readonly")
        self.playlist_box.pack(side="left", fill="x", expand=True)
        self.playlist_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_playlist_tracks())

        ttk.Button(playlist_top, text="+", width=3, command=self.new_playlist).pack(side="left", padx=2)
        ttk.Button(playlist_top, text="Rename", command=self.rename_playlist).pack(side="left", padx=2)
        ttk.Button(playlist_top, text="Del", command=self.delete_playlist).pack(side="left")

        self.playlist_tracks = tk.Listbox(right, activestyle="none")
        style_listbox(self.playlist_tracks)
        self.playlist_tracks.grid(row=5, column=0, sticky="nsew")
        self.playlist_tracks.bind("<Double-1>", self.play_playlist_track)

        playlist_buttons = ttk.Frame(right)
        playlist_buttons.grid(row=6, column=0, sticky="ew", pady=4)

        ttk.Button(playlist_buttons, text="Add Selected File", command=self.add_selected_to_playlist).pack(side="left")
        ttk.Button(playlist_buttons, text="Remove Track", command=self.remove_playlist_track).pack(side="left", padx=4)
        ttk.Button(playlist_buttons, text="Play Playlist", command=self.play_playlist).pack(side="right")

        bottom = ttk.Frame(self.root, style="Panel.TFrame")
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        bottom.columnconfigure(1, weight=1)

        self.now_label = ttk.Label(bottom, text="Nothing playing")
        self.now_label.grid(row=0, column=0, columnspan=6, sticky="w")

        self.time_label = ttk.Label(bottom, text="0:00 / 0:00")
        self.time_label.grid(row=1, column=0, sticky="w", padx=(0, 8))

        self.seek_var = tk.DoubleVar(value=0)
        self.seek_slider = ttk.Scale(bottom, from_=0, to=100, variable=self.seek_var, orient="horizontal")
        self.seek_slider.grid(row=1, column=1, columnspan=5, sticky="ew")
        self.seek_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "dragging_seek", True))
        self.seek_slider.bind("<ButtonRelease-1>", self.seek_release)

        controls = ttk.Frame(bottom)
        controls.grid(row=2, column=0, columnspan=6, sticky="ew", pady=6)

        ttk.Button(controls, text="⏮ Prev", command=self.prev_track).pack(side="left")
        ttk.Button(controls, text=f"⏪ -{SEEK_SECONDS}s", command=lambda: self.mixer.seek_seconds(-SEEK_SECONDS)).pack(side="left", padx=3)
        ttk.Button(controls, text="▶/⏸ Play/Pause", command=self.play_pause).pack(side="left", padx=3)
        ttk.Button(controls, text="↺ Replay", command=self.replay).pack(side="left", padx=3)
        ttk.Button(controls, text=f"+{SEEK_SECONDS}s ⏩", command=lambda: self.mixer.seek_seconds(SEEK_SECONDS)).pack(side="left", padx=3)
        ttk.Button(controls, text="Next ⏭", command=self.next_track).pack(side="left", padx=3)
        ttk.Button(controls, text="⏹ Stop", command=self.stop).pack(side="left", padx=12)

        self.autoplay_var = tk.BooleanVar(value=bool(self.cfg.data.get("autoplay", True)))
        ttk.Checkbutton(
            controls,
            text="Autoplay next",
            variable=self.autoplay_var,
            command=self.save_playback_options,
        ).pack(side="left")

        self.loop_song_var = tk.BooleanVar(value=bool(self.cfg.data.get("loop_song", False)))
        ttk.Checkbutton(
            controls,
            text="Loop song",
            variable=self.loop_song_var,
            command=self.save_playback_options,
        ).pack(side="left", padx=(8, 0))

        self.loop_playlist_var = tk.BooleanVar(value=bool(self.cfg.data.get("loop_playlist", False)))
        ttk.Checkbutton(
            controls,
            text="Loop playlist",
            variable=self.loop_playlist_var,
            command=self.save_playback_options,
        ).pack(side="left", padx=(8, 0))

    def change_theme(self, event=None):
        mode = "light" if self.theme_var.get().lower() == "light" else "dark"
        self.cfg.data["theme"] = mode
        self.cfg.save()
        apply_theme(self.root, mode)
        refresh_manual_widget_theme(self)
        self.update_relay_status(show_error=False)

    def refresh_devices(self):
        outputs = {}
        inputs = {"No microphone": "none"}

        if output_channels_supported(None) is not None:
            outputs["System default"] = None

        if input_channels_supported(None) is not None:
            inputs["System default"] = None

        try:
            for i, dev in enumerate(sd.query_devices()):
                name = dev.get("name", f"Device {i}")

                if dev.get("max_output_channels", 0) > 0:
                    if output_channels_supported(i) is not None:
                        outputs[f"{i}: {name}"] = i

                if dev.get("max_input_channels", 0) > 0:
                    if input_channels_supported(i) is not None:
                        inputs[f"{i}: {name}"] = i

        except Exception as e:
            messagebox.showerror("Device Error", str(e))
            return

        if not outputs:
            outputs["System default"] = None

        self.output_devices = outputs
        self.input_devices = inputs

        self.monitor_box["values"] = list(outputs.keys())
        self.mic_box["values"] = list(inputs.keys())

        self.select_device_label(self.monitor_var, outputs, self.cfg.data.get("monitor_device"))
        self.select_device_label(
            self.mic_var,
            inputs,
            self.cfg.data.get("mic_device", "none"),
            default_label="No microphone",
        )

        self.apply_selected_devices()
        self.update_relay_status(show_error=True)

    def update_relay_status(self, show_error=False):
        idx, name = find_vb_cable_relay_output()

        if idx is None:
            self.relay_status.config(
                text="VB-Cable not found",
                fg=THEME_BAD,
                bg=THEME_PANEL,
            )

            if show_error and not self.vb_error_shown:
                self.vb_error_shown = True
                messagebox.showerror(
                    "VB Virtual Audio Cable Not Found",
                    "SoundDeck could not find VB-Audio Virtual Cable.\n\n"
                    "Install VB-Audio Virtual Cable, restart your PC, then reopen SoundDeck.\n\n"
                    "Check README.md for setup instructions.",
                )
        else:
            self.relay_status.config(
                text=f"Connected automatically: {name}",
                fg=THEME_GOOD,
                bg=THEME_PANEL,
            )
            self.vb_error_shown = False

    def select_device_label(self, var, mapping, saved_value, default_label="System default"):
        for label, value in mapping.items():
            if value == saved_value:
                var.set(label)
                return

        if default_label in mapping:
            var.set(default_label)
            return

        var.set(next(iter(mapping.keys())))

    def apply_selected_devices(self, event=None):
        monitor = self.output_devices.get(self.monitor_var.get(), None)
        mic = self.input_devices.get(self.mic_var.get(), "none")
        self.mixer.set_devices(monitor, mic)
        self.update_relay_status(show_error=False)

    def save_routing_options(self):
        self.mixer.set_toggles(
            self.mic_passthrough_var.get(),
            self.monitor_sound_var.get(),
            self.monitor_mic_var.get(),
        )
        self.update_relay_status(show_error=False)

    def set_volume(self, value):
        value = float(value)
        self.mixer.set_volume(value)
        self.volume_label.config(text=f"{int(value * 100)}%")

    def set_mic_volume(self, value):
        value = float(value)
        self.mixer.set_mic_volume(value)
        self.mic_volume_label.config(text=f"{int(value * 100)}%")

    def set_monitor_volume(self, value):
        value = float(value)
        self.mixer.set_monitor_volume(value)
        self.monitor_volume_label.config(text=f"{int(value * 100)}%")

    def ffmpeg_check(self):
        ffmpeg_test = "Not tested"

        if FFMPEG_EXE and os.path.exists(FFMPEG_EXE):
            try:
                result = subprocess.run(
                    [FFMPEG_EXE, "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess_flags(),
                )

                if result.returncode == 0:
                    first_line = result.stdout.decode("utf-8", errors="replace").splitlines()[0]
                    ffmpeg_test = f"OK\n{first_line}"
                else:
                    ffmpeg_test = result.stderr.decode("utf-8", errors="replace")
            except Exception as e:
                ffmpeg_test = f"FAILED:\n{e}"

        relay_idx, relay_name = find_vb_cable_relay_output()
        relay_test = f"{relay_idx}: {relay_name}" if relay_idx is not None else "NOT FOUND"

        msg = (
            f"Auto Relay VB-Cable Device:\n{relay_test}\n\n"
            f"FFMPEG_FOLDER:\n{FFMPEG_FOLDER}\n\n"
            f"FFMPEG_EXE:\n{FFMPEG_EXE}\n"
            f"Exists: {os.path.exists(FFMPEG_EXE) if FFMPEG_EXE else False}\n\n"
            f"FFPROBE_EXE:\n{FFPROBE_EXE}\n"
            f"Exists: {os.path.exists(FFPROBE_EXE) if FFPROBE_EXE else False}\n\n"
            f"Direct ffmpeg.exe test:\n{ffmpeg_test}\n\n"
            f"Sample rate: {SAMPLE_RATE}"
        )

        messagebox.showinfo("SoundDeck Check", msg)

    def add_folder(self):
        folder = filedialog.askdirectory(title="Add audio folder")
        if folder and folder not in self.cfg.data["folders"]:
            self.cfg.data["folders"].append(folder)
            self.cfg.save()
            self.refresh_library()

    def remove_folder(self):
        folders = self.cfg.data.get("folders", [])

        if not folders:
            messagebox.showinfo("No folders", "No folders added yet.")
            return

        text = "\n".join(f"{i + 1}. {folder}" for i, folder in enumerate(folders))
        choice = simpledialog.askinteger("Remove Folder", f"Enter number to remove:\n\n{text}")

        if choice and 1 <= choice <= len(folders):
            folders.pop(choice - 1)
            self.cfg.save()
            self.refresh_library()

    def refresh_library(self):
        self.lib.scan()
        self.refresh_list_only()

    def refresh_list_only(self):
        query = self.search_entry.get()
        self.visible = self.lib.search(query)

        self.library_list.delete(0, tk.END)
        for path in self.visible:
            self.library_list.insert(tk.END, Path(path).name)

    def get_selected_library_path(self):
        selected = self.library_list.curselection()
        if not selected:
            return None

        idx = selected[0]
        if idx < 0 or idx >= len(self.visible):
            return None

        return self.visible[idx]

    def play_path(self, path):
        if not path:
            return

        if not os.path.exists(path):
            messagebox.showwarning("Missing file", path)
            return

        if find_vb_cable_relay_output()[0] is None:
            self.update_relay_status(show_error=True)
            return

        try:
            self.mixer.load(path)
            self.mixer.play()
            self.now_label.config(text=f"Playing: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def play_selected_file(self, event=None):
        path = self.get_selected_library_path()
        if path:
            self.queue_index = -1
            self.play_path(path)

    def library_right_click(self, event):
        nearest = self.library_list.nearest(event.y)

        if nearest >= 0:
            self.library_list.selection_clear(0, tk.END)
            self.library_list.selection_set(nearest)

        path = self.get_selected_library_path()
        if not path:
            return

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Play Now", command=lambda: self.play_path(path))
        menu.add_command(label="Add to Queue", command=lambda: self.add_path_to_queue(path))
        menu.add_command(label="Add to Playlist", command=lambda: self.add_path_to_playlist(path))
        menu.tk_popup(event.x_root, event.y_root)

    def add_path_to_queue(self, path):
        self.queue.append(path)
        self.queue_list.insert(tk.END, Path(path).name)

    def add_selected_to_queue(self):
        path = self.get_selected_library_path()
        if path:
            self.add_path_to_queue(path)

    def remove_selected_queue(self):
        selected = self.queue_list.curselection()
        if not selected:
            return

        idx = selected[0]
        if 0 <= idx < len(self.queue):
            self.queue.pop(idx)
            self.queue_list.delete(idx)

            if self.queue_index == idx:
                self.queue_index = -1
            elif self.queue_index > idx:
                self.queue_index -= 1

    def clear_queue(self):
        self.queue.clear()
        self.queue_index = -1
        self.queue_list.delete(0, tk.END)

    def play_queue_index(self, idx):
        if 0 <= idx < len(self.queue):
            self.queue_index = idx

            self.queue_list.selection_clear(0, tk.END)
            self.queue_list.selection_set(idx)
            self.queue_list.see(idx)

            self.play_path(self.queue[idx])

    def play_queue_selected(self, event=None):
        selected = self.queue_list.curselection()
        if selected:
            self.play_queue_index(selected[0])

    def play_pause(self):
        if self.mixer.audio is not None and self.mixer.is_playing:
            self.mixer.pause_toggle()
            return

        if self.mixer.audio is not None:
            self.mixer.play()
            return

        if self.queue:
            self.play_queue_index(0)
            return

        self.play_selected_file()

    def replay(self):
        if find_vb_cable_relay_output()[0] is None:
            self.update_relay_status(show_error=True)
            return

        if self.mixer.audio is not None:
            self.mixer.restart()

    def stop(self):
        self.mixer.stop()
        self.now_label.config(text="Stopped")

    def next_track(self):
        if self.queue_index + 1 < len(self.queue):
            self.play_queue_index(self.queue_index + 1)
            return

        if self.loop_playlist_var.get() and self.queue:
            self.play_queue_index(0)

    def prev_track(self):
        if self.mixer.pos_seconds > 3:
            self.mixer.seek_percent(0)
            return

        if self.queue_index > 0:
            self.play_queue_index(self.queue_index - 1)
            return

        if self.loop_playlist_var.get() and self.queue:
            self.play_queue_index(len(self.queue) - 1)
            return

        self.mixer.seek_percent(0)

    def finished_track(self):
        if self.loop_song_var.get() and self.mixer.audio is not None:
            self.mixer.restart()
            return

        if self.autoplay_var.get() and self.queue_index + 1 < len(self.queue):
            self.play_queue_index(self.queue_index + 1)
            return

        if self.loop_playlist_var.get() and self.queue:
            self.play_queue_index(0)
            return

        self.now_label.config(text="Finished")

    def seek_release(self, event=None):
        self.dragging_seek = False
        self.mixer.seek_percent(self.seek_var.get() / 100.0)

    def save_playback_options(self):
        self.cfg.data["autoplay"] = bool(self.autoplay_var.get())
        self.cfg.data["loop_song"] = bool(self.loop_song_var.get())
        self.cfg.data["loop_playlist"] = bool(self.loop_playlist_var.get())
        self.cfg.save()

    def refresh_playlists(self):
        names = sorted(self.cfg.data.get("playlists", {}).keys())
        self.playlist_box["values"] = names

        if names and self.playlist_var.get() not in names:
            self.playlist_var.set(names[0])
        elif not names:
            self.playlist_var.set("")

        self.refresh_playlist_tracks()

    def refresh_playlist_tracks(self):
        self.playlist_tracks.delete(0, tk.END)

        name = self.playlist_var.get()
        if not name:
            return

        for path in self.cfg.data["playlists"].get(name, []):
            label = Path(path).name
            if not os.path.exists(path):
                label += "  [missing]"
            self.playlist_tracks.insert(tk.END, label)

    def new_playlist(self):
        name = simpledialog.askstring("New Playlist", "Playlist name:")
        if not name:
            return

        self.cfg.data["playlists"].setdefault(name, [])
        self.cfg.save()

        self.playlist_var.set(name)
        self.refresh_playlists()

    def rename_playlist(self):
        old = self.playlist_var.get()
        if not old:
            return

        new = simpledialog.askstring("Rename Playlist", "New name:", initialvalue=old)
        if not new or new == old:
            return

        if new in self.cfg.data["playlists"]:
            messagebox.showwarning("Already exists", "A playlist with that name already exists.")
            return

        self.cfg.data["playlists"][new] = self.cfg.data["playlists"].pop(old)
        self.cfg.save()

        self.playlist_var.set(new)
        self.refresh_playlists()

    def delete_playlist(self):
        name = self.playlist_var.get()
        if not name:
            return

        if messagebox.askyesno("Delete Playlist", f'Delete "{name}"?'):
            self.cfg.data["playlists"].pop(name, None)
            self.cfg.save()
            self.playlist_var.set("")
            self.refresh_playlists()

    def add_path_to_playlist(self, path):
        name = self.playlist_var.get()

        if not name:
            name = simpledialog.askstring("Playlist", "Playlist name:")
            if not name:
                return
            self.cfg.data["playlists"].setdefault(name, [])
            self.playlist_var.set(name)

        self.cfg.data["playlists"].setdefault(name, [])

        if path not in self.cfg.data["playlists"][name]:
            self.cfg.data["playlists"][name].append(path)

        self.cfg.save()
        self.refresh_playlists()

    def add_selected_to_playlist(self):
        path = self.get_selected_library_path()
        if path:
            self.add_path_to_playlist(path)

    def remove_playlist_track(self):
        name = self.playlist_var.get()
        selected = self.playlist_tracks.curselection()

        if not name or not selected:
            return

        tracks = self.cfg.data["playlists"].get(name, [])
        idx = selected[0]

        if 0 <= idx < len(tracks):
            tracks.pop(idx)
            self.cfg.save()
            self.refresh_playlist_tracks()

    def play_playlist_track(self, event=None):
        name = self.playlist_var.get()
        selected = self.playlist_tracks.curselection()

        if not name or not selected:
            return

        tracks = self.cfg.data["playlists"].get(name, [])
        idx = selected[0]

        if 0 <= idx < len(tracks):
            self.play_path(tracks[idx])

    def play_playlist(self):
        name = self.playlist_var.get()
        if not name:
            return

        tracks = [
            path
            for path in self.cfg.data["playlists"].get(name, [])
            if os.path.exists(path)
        ]

        if not tracks:
            messagebox.showinfo("Empty Playlist", "No valid tracks in this playlist.")
            return

        self.clear_queue()

        for path in tracks:
            self.add_path_to_queue(path)

        self.play_queue_index(0)

    def show_audio_error(self, msg):
        self.now_label.config(text="Audio error")
        messagebox.showerror("Audio Error", msg)

    def tick(self):
        duration = self.mixer.dur_seconds
        position = self.mixer.pos_seconds

        self.time_label.config(text=f"{fmt_time(position)} / {fmt_time(duration)}")

        if duration > 0 and not self.dragging_seek:
            self.seek_var.set(max(0, min(100, (position / duration) * 100)))

        if self.mixer.consume_finished():
            self.finished_track()

        self.root.after(200, self.tick)

    def close(self):
        self.mixer.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
