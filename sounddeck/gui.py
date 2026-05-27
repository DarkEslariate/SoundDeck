import os
import sys
import subprocess
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from .constants import APP_NAME, APP_VERSION, SEEK_SECONDS, app_dir
from .theme import apply_theme, style_listbox, style_label, THEME
from .config import Config
from .library import Library
from .audio_engine import AudioMixer
from .decoder import decode_audio_file, find_bundled_ffmpeg
from .devices import list_output_devices, list_input_devices, find_vb_cable_relay_output

try:
    import keyboard
except Exception:
    keyboard = None

def fmt_time(seconds):
    seconds = int(max(0, seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

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
        self.hotkey_handles = []
        self.grid_window = None
        self.setup_window = None
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1380x820")
        self.root.minsize(1120, 720)
        apply_theme(self.root, self.cfg.data.get("theme", "dark"))
        self.build_ui()
        self.refresh_devices()
        self.refresh_library()
        self.refresh_playlists()
        self.register_hotkeys()
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
        ttk.Button(top, text="Setup Wizard", command=self.open_setup_wizard).pack(side="left", padx=4)
        ttk.Button(top, text="FFmpeg Check", command=self.ffmpeg_check).pack(side="left", padx=4)
        ttk.Button(top, text="Grid Mode", command=self.open_grid).pack(side="left", padx=4)
        ttk.Button(top, text="Import Config", command=self.import_config).pack(side="left", padx=4)
        ttk.Button(top, text="Export Config", command=self.export_config).pack(side="left", padx=4)
        ttk.Label(top, text="Theme:", style="Panel.TLabel").pack(side="left", padx=(12, 4))
        self.theme_var = tk.StringVar(value="Light" if self.cfg.data.get("theme") == "light" else "Dark")
        self.theme_box = ttk.Combobox(top, textvariable=self.theme_var, state="readonly", width=8, values=["Dark", "Light"])
        self.theme_box.pack(side="left")
        self.theme_box.bind("<<ComboboxSelected>>", self.change_theme)
        self.setup_tip = ttk.Label(top, text="Discord/OBS input: CABLE Output. SoundDeck automatically relays to CABLE Input.", style="Panel.TLabel")
        self.setup_tip.pack(side="left", padx=12)
        routing = ttk.LabelFrame(self.root, text="Routing")
        routing.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6))
        for c in (1, 3, 5):
            routing.columnconfigure(c, weight=1)
        ttk.Label(routing, text="Auto Relay:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.relay_status = tk.Label(routing, text="Checking VB-Cable...", anchor="w", bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 10, "bold"))
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
        ttk.Checkbutton(routing, text="Send mic to apps", variable=self.mic_passthrough_var, command=self.save_routing_options).grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.monitor_sound_var = tk.BooleanVar(value=bool(self.cfg.data.get("monitor_sound", True)))
        ttk.Checkbutton(routing, text="Hear soundboard", variable=self.monitor_sound_var, command=self.save_routing_options).grid(row=1, column=1, sticky="w", padx=4, pady=4)
        self.monitor_mic_var = tk.BooleanVar(value=bool(self.cfg.data.get("monitor_mic", False)))
        ttk.Checkbutton(routing, text="Hear yourself", variable=self.monitor_mic_var, command=self.save_routing_options).grid(row=1, column=2, sticky="w", padx=6, pady=4)
        self.allow_overlap_var = tk.BooleanVar(value=bool(self.cfg.data.get("allow_overlap", True)))
        ttk.Checkbutton(routing, text="Allow overlapping sounds", variable=self.allow_overlap_var, command=self.save_playback_options).grid(row=1, column=3, sticky="w", padx=6, pady=4)
        self.normalize_var = tk.BooleanVar(value=bool(self.cfg.data.get("normalize_audio", False)))
        ttk.Checkbutton(routing, text="Normalize loaded sounds", variable=self.normalize_var, command=self.save_playback_options).grid(row=1, column=4, sticky="w", padx=6, pady=4)
        self.master_limiter_var = tk.BooleanVar(value=bool(self.cfg.data.get("master_limiter", True)))
        ttk.Checkbutton(routing, text="Master limiter", variable=self.master_limiter_var, command=self.save_routing_options).grid(row=1, column=5, sticky="w", padx=6, pady=4)
        ttk.Label(routing, text="Sound Vol").grid(row=2, column=0, sticky="w", padx=6)
        self.volume_slider = ttk.Scale(routing, from_=0, to=2.5, orient="horizontal", command=self.set_volume)
        self.volume_slider.set(float(self.cfg.data.get("volume", 1.0)))
        self.volume_slider.grid(row=2, column=1, sticky="ew", padx=4)
        self.volume_label = ttk.Label(routing, text=f"{int(float(self.cfg.data.get('volume', 1.0)) * 100)}%")
        self.volume_label.grid(row=2, column=2, sticky="w", padx=4)
        ttk.Label(routing, text="Mic Vol").grid(row=2, column=3, sticky="e", padx=4)
        self.mic_volume_slider = ttk.Scale(routing, from_=0, to=2.5, orient="horizontal", command=self.set_mic_volume)
        self.mic_volume_slider.set(float(self.cfg.data.get("mic_volume", 1.0)))
        self.mic_volume_slider.grid(row=2, column=4, sticky="ew", padx=4)
        self.mic_volume_label = ttk.Label(routing, text=f"{int(float(self.cfg.data.get('mic_volume', 1.0)) * 100)}%")
        self.mic_volume_label.grid(row=2, column=5, sticky="w", padx=4)
        ttk.Label(routing, text="Monitor Vol").grid(row=3, column=0, sticky="w", padx=6)
        self.monitor_volume_slider = ttk.Scale(routing, from_=0, to=2.5, orient="horizontal", command=self.set_monitor_volume)
        self.monitor_volume_slider.set(float(self.cfg.data.get("monitor_volume", 1.0)))
        self.monitor_volume_slider.grid(row=3, column=1, sticky="ew", padx=4)
        self.monitor_volume_label = ttk.Label(routing, text=f"{int(float(self.cfg.data.get('monitor_volume', 1.0)) * 100)}%")
        self.monitor_volume_label.grid(row=3, column=2, sticky="w", padx=4)
        main = ttk.Frame(self.root)
        main.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=6)
        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)
        left = ttk.Frame(main, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        ttk.Label(left, text="Library").grid(row=0, column=0, sticky="w")
        self.search_entry = ttk.Entry(left)
        self.search_entry.grid(row=1, column=0, sticky="ew", pady=4)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list_only())
        lib_buttons = ttk.Frame(left)
        lib_buttons.grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(lib_buttons, text="Play", command=self.play_selected_file).pack(side="left")
        ttk.Button(lib_buttons, text="Play Overlap", command=self.play_selected_overlap).pack(side="left", padx=3)
        ttk.Button(lib_buttons, text="Queue", command=self.add_selected_to_queue).pack(side="left", padx=3)
        ttk.Button(lib_buttons, text="Favorite", command=self.toggle_selected_favorite).pack(side="left", padx=3)
        ttk.Button(lib_buttons, text="Tags", command=self.edit_selected_tags).pack(side="left", padx=3)
        ttk.Button(lib_buttons, text="Sound Settings", command=self.edit_selected_sound_settings).pack(side="left", padx=3)
        ttk.Button(lib_buttons, text="Pin Grid", command=self.pin_selected_to_grid).pack(side="left", padx=3)
        self.library_list = tk.Listbox(left, activestyle="none")
        style_listbox(self.library_list)
        self.library_list.grid(row=3, column=0, sticky="nsew")
        self.library_list.bind("<Double-1>", self.library_double_click)
        self.library_list.bind("<Button-3>", self.library_right_click)
        right = ttk.Notebook(main)
        right.grid(row=0, column=1, sticky="nsew")
        queue_tab = ttk.Frame(right, style="Panel.TFrame")
        playlist_tab = ttk.Frame(right, style="Panel.TFrame")
        fav_tab = ttk.Frame(right, style="Panel.TFrame")
        recent_tab = ttk.Frame(right, style="Panel.TFrame")
        right.add(queue_tab, text="Queue")
        right.add(playlist_tab, text="Playlists")
        right.add(fav_tab, text="Favorites")
        right.add(recent_tab, text="Recent")
        queue_tab.columnconfigure(0, weight=1)
        queue_tab.rowconfigure(0, weight=1)
        self.queue_list = tk.Listbox(queue_tab, height=9, activestyle="none")
        style_listbox(self.queue_list)
        self.queue_list.grid(row=0, column=0, sticky="nsew")
        self.queue_list.bind("<Double-1>", lambda e: self.play_queue_selected())
        qbtn = ttk.Frame(queue_tab)
        qbtn.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(qbtn, text="Remove", command=self.remove_selected_queue).pack(side="left")
        ttk.Button(qbtn, text="Clear", command=self.clear_queue).pack(side="left", padx=4)
        playlist_tab.columnconfigure(0, weight=1)
        playlist_tab.rowconfigure(2, weight=1)
        pltop = ttk.Frame(playlist_tab)
        pltop.grid(row=0, column=0, sticky="ew", pady=4)
        self.playlist_var = tk.StringVar()
        self.playlist_box = ttk.Combobox(pltop, textvariable=self.playlist_var, state="readonly")
        self.playlist_box.pack(side="left", fill="x", expand=True)
        self.playlist_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_playlist_tracks())
        ttk.Button(pltop, text="+", width=3, command=self.new_playlist).pack(side="left", padx=2)
        ttk.Button(pltop, text="Rename", command=self.rename_playlist).pack(side="left", padx=2)
        ttk.Button(pltop, text="Del", command=self.delete_playlist).pack(side="left")
        plbtn = ttk.Frame(playlist_tab)
        plbtn.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(plbtn, text="Add Selected", command=self.add_selected_to_playlist).pack(side="left")
        ttk.Button(plbtn, text="Remove Track", command=self.remove_playlist_track).pack(side="left", padx=4)
        ttk.Button(plbtn, text="Export", command=self.export_playlist).pack(side="left", padx=4)
        ttk.Button(plbtn, text="Import", command=self.import_playlist).pack(side="left", padx=4)
        ttk.Button(plbtn, text="Play Playlist", command=self.play_playlist).pack(side="right")
        self.playlist_tracks = tk.Listbox(playlist_tab, activestyle="none")
        style_listbox(self.playlist_tracks)
        self.playlist_tracks.grid(row=2, column=0, sticky="nsew")
        self.playlist_tracks.bind("<Double-1>", lambda e: self.play_playlist_track())
        fav_tab.columnconfigure(0, weight=1)
        fav_tab.rowconfigure(0, weight=1)
        self.fav_list = tk.Listbox(fav_tab, activestyle="none")
        style_listbox(self.fav_list)
        self.fav_list.grid(row=0, column=0, sticky="nsew")
        self.fav_list.bind("<Double-1>", lambda e: self.play_listbox_path(self.fav_list, self.cfg.data.get("favorites", [])))
        recent_tab.columnconfigure(0, weight=1)
        recent_tab.rowconfigure(0, weight=1)
        self.recent_list = tk.Listbox(recent_tab, activestyle="none")
        style_listbox(self.recent_list)
        self.recent_list.grid(row=0, column=0, sticky="nsew")
        self.recent_list.bind("<Double-1>", lambda e: self.play_listbox_path(self.recent_list, self.cfg.data.get("recent", [])))
        bottom = ttk.Frame(self.root, style="Panel.TFrame")
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        bottom.columnconfigure(1, weight=1)
        self.now_label = ttk.Label(bottom, text="Nothing playing")
        self.now_label.grid(row=0, column=0, columnspan=6, sticky="w")
        self.layers_label = ttk.Label(bottom, text="0 overlapping")
        self.layers_label.grid(row=0, column=6, sticky="e")
        self.time_label = ttk.Label(bottom, text="0:00 / 0:00")
        self.time_label.grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.seek_var = tk.DoubleVar(value=0)
        self.seek_slider = ttk.Scale(bottom, from_=0, to=100, variable=self.seek_var, orient="horizontal")
        self.seek_slider.grid(row=1, column=1, columnspan=6, sticky="ew")
        self.seek_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "dragging_seek", True))
        self.seek_slider.bind("<ButtonRelease-1>", self.seek_release)
        controls = ttk.Frame(bottom)
        controls.grid(row=2, column=0, columnspan=7, sticky="ew", pady=6)
        ttk.Button(controls, text="Prev", command=self.prev_track).pack(side="left")
        ttk.Button(controls, text=f"-{SEEK_SECONDS}s", command=lambda: self.mixer.seek_seconds(-SEEK_SECONDS)).pack(side="left", padx=3)
        ttk.Button(controls, text="Play/Pause", command=self.play_pause).pack(side="left", padx=3)
        ttk.Button(controls, text="Replay", command=self.replay).pack(side="left", padx=3)
        ttk.Button(controls, text=f"+{SEEK_SECONDS}s", command=lambda: self.mixer.seek_seconds(SEEK_SECONDS)).pack(side="left", padx=3)
        ttk.Button(controls, text="Next", command=self.next_track).pack(side="left", padx=3)
        ttk.Button(controls, text="Stop", command=self.stop).pack(side="left", padx=8)
        ttk.Button(controls, text="Stop Overlaps", command=self.stop_overlaps).pack(side="left", padx=3)
        ttk.Button(controls, text="Stop All", command=self.stop_all).pack(side="left", padx=3)
        self.autoplay_var = tk.BooleanVar(value=bool(self.cfg.data.get("autoplay", True)))
        ttk.Checkbutton(controls, text="Autoplay next", variable=self.autoplay_var, command=self.save_playback_options).pack(side="left")
        self.loop_song_var = tk.BooleanVar(value=bool(self.cfg.data.get("loop_song", False)))
        ttk.Checkbutton(controls, text="Loop song", variable=self.loop_song_var, command=self.save_playback_options).pack(side="left", padx=(8, 0))
        self.loop_playlist_var = tk.BooleanVar(value=bool(self.cfg.data.get("loop_playlist", False)))
        ttk.Checkbutton(controls, text="Loop playlist", variable=self.loop_playlist_var, command=self.save_playback_options).pack(side="left", padx=(8, 0))
        self.global_hotkeys_var = tk.BooleanVar(value=bool(self.cfg.data.get("global_hotkeys", False)))
        ttk.Checkbutton(controls, text="Global hotkeys", variable=self.global_hotkeys_var, command=self.toggle_global_hotkeys).pack(side="left", padx=(8, 0))

    def change_theme(self, event=None):
        mode = "light" if self.theme_var.get().lower() == "light" else "dark"
        self.cfg.data["theme"] = mode
        self.cfg.save()
        apply_theme(self.root, mode)
        for widget in (self.library_list, self.queue_list, self.playlist_tracks, self.fav_list, self.recent_list):
            style_listbox(widget)
        style_label(self.relay_status, "muted")
        self.update_relay_status(show_error=False)

    def refresh_devices(self):
        self.output_devices = list_output_devices()
        self.input_devices = list_input_devices()
        self.monitor_box["values"] = list(self.output_devices.keys())
        self.mic_box["values"] = list(self.input_devices.keys())
        self.select_device_label(self.monitor_var, self.output_devices, self.cfg.data.get("monitor_device"))
        self.select_device_label(self.mic_var, self.input_devices, self.cfg.data.get("mic_device", "none"), default_label="No microphone")
        self.apply_selected_devices()
        self.update_relay_status(show_error=True)

    def select_device_label(self, var, mapping, saved_value, default_label="System default"):
        for label, value in mapping.items():
            if value == saved_value:
                var.set(label)
                return
        if default_label in mapping:
            var.set(default_label)
            return
        if mapping:
            var.set(next(iter(mapping.keys())))

    def update_relay_status(self, show_error=False):
        idx, name = find_vb_cable_relay_output()
        if idx is None:
            self.relay_status.config(text="VB-Cable not found. Run Setup Wizard.", fg=THEME["bad"], bg=THEME["panel"])
            if show_error and not self.vb_error_shown:
                self.vb_error_shown = True
                self.open_setup_wizard(auto=True)
        else:
            self.relay_status.config(text=f"Connected automatically: {name}", fg=THEME["good"], bg=THEME["panel"])
            self.vb_error_shown = False

    def open_setup_wizard(self, auto=False):
        if self.setup_window and self.setup_window.winfo_exists():
            self.setup_window.lift()
            return
        win = tk.Toplevel(self.root)
        self.setup_window = win
        win.title("SoundDeck Setup Wizard")
        win.geometry("660x560")
        win.configure(bg=THEME["bg"])
        win.transient(self.root)
        box = ttk.Frame(win, style="Panel.TFrame")
        box.pack(fill="both", expand=True, padx=14, pady=14)
        title = tk.Label(box, text="SoundDeck Setup Wizard", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 15, "bold"))
        title.pack(anchor="w", pady=(0, 10))
        idx, name = find_vb_cable_relay_output()
        status_text = "VB-Cable is installed and ready." if idx is not None else "VB-Cable was not found."
        status_kind = "good" if idx is not None else "bad"
        status = tk.Label(box, text=status_text, bg=THEME["panel"], fg=THEME[status_kind], font=("Segoe UI", 11, "bold"))
        status.pack(anchor="w", pady=(0, 10))
        text = (
            "SoundDeck uses VB-Audio Virtual Cable to send soundboard audio into Discord, OBS, games, and voice chat apps.\n\n"
            "If it is missing, install it from the official VB-Audio page, run the installer as administrator, reboot your PC, then open SoundDeck again.\n\n"
            "After it is installed, set Discord or OBS microphone/input to CABLE Output. SoundDeck will automatically relay soundboard audio to CABLE Input."
        )
        body = tk.Label(box, text=text, bg=THEME["panel"], fg=THEME["text"], justify="left", wraplength=600)
        body.pack(anchor="w", pady=(0, 12))
        steps = tk.Label(
            box,
            text="1. Open official VB-Audio download page\n2. Download VB-CABLE Driver Pack\n3. Extract the ZIP\n4. Run VBCABLE_Setup_x64.exe as administrator\n5. Install Driver\n6. Restart your PC\n7. Reopen SoundDeck and click Re-check",
            bg=THEME["panel"],
            fg=THEME["muted"],
            justify="left",
            wraplength=600
        )
        steps.pack(anchor="w", pady=(0, 12))
        options = ttk.LabelFrame(box, text="Setup Options")
        options.pack(fill="x", pady=(0, 12))
        add_shortcut_var = tk.BooleanVar(value=True)
        run_after_var = tk.BooleanVar(value=False)
        startup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text="Add SoundDeck shortcut to desktop", variable=add_shortcut_var).pack(anchor="w", padx=8, pady=(6, 2))
        ttk.Checkbutton(options, text="Run SoundDeck after closing this wizard", variable=run_after_var).pack(anchor="w", padx=8, pady=2)
        ttk.Checkbutton(options, text="Start SoundDeck when Windows starts", variable=startup_var).pack(anchor="w", padx=8, pady=(2, 6))
        result = tk.Label(box, text="", bg=THEME["panel"], fg=THEME["muted"], justify="left", wraplength=600)
        result.pack(anchor="w", pady=(0, 8))
        buttons = ttk.Frame(box, style="Panel.TFrame")
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Open Official Download Page", command=lambda: webbrowser.open("https://vb-audio.com/Cable/")).pack(side="left")
        ttk.Button(buttons, text="Apply Options", command=lambda: self.apply_setup_options(add_shortcut_var.get(), run_after_var.get(), startup_var.get(), result, win)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Re-check", command=lambda: self.recheck_setup_wizard(status, result)).pack(side="left")
        ttk.Button(buttons, text="Close", command=win.destroy).pack(side="right")
        if auto:
            win.lift()

    def setup_launch_target(self):
        if getattr(sys, "frozen", False):
            return sys.executable, "", app_dir()
        script = os.path.join(app_dir(), "SoundDeck.py")
        return sys.executable, f'"{script}"', app_dir()

    def powershell_quote(self, value):
        return str(value).replace("'", "''")

    def create_shortcut(self, shortcut_path):
        target, arguments, working_dir = self.setup_launch_target()
        icon = target if os.path.exists(target) else ""
        ps = (
            "$w=New-Object -ComObject WScript.Shell;"
            f"$s=$w.CreateShortcut('{self.powershell_quote(shortcut_path)}');"
            f"$s.TargetPath='{self.powershell_quote(target)}';"
            f"$s.Arguments='{self.powershell_quote(arguments)}';"
            f"$s.WorkingDirectory='{self.powershell_quote(working_dir)}';"
            f"$s.IconLocation='{self.powershell_quote(icon)}';"
            "$s.Save()"
        )
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True, creationflags=0x08000000)

    def create_desktop_shortcut(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut = os.path.join(desktop, "SoundDeck.lnk")
        self.create_shortcut(shortcut)

    def create_startup_shortcut(self):
        startup = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        os.makedirs(startup, exist_ok=True)
        shortcut = os.path.join(startup, "SoundDeck.lnk")
        self.create_shortcut(shortcut)

    def launch_new_sounddeck_instance(self):
        target, arguments, working_dir = self.setup_launch_target()
        if arguments:
            subprocess.Popen([target, arguments.strip('"')], cwd=working_dir)
        else:
            subprocess.Popen([target], cwd=working_dir)

    def apply_setup_options(self, add_shortcut, run_after, startup, result, window):
        messages = []
        try:
            if add_shortcut:
                self.create_desktop_shortcut()
                messages.append("Desktop shortcut created.")
            if startup:
                self.create_startup_shortcut()
                messages.append("Windows startup shortcut created.")
            if run_after:
                messages.append("SoundDeck will open after this wizard closes.")
            if not messages:
                messages.append("No setup options were selected.")
            result.config(text="\n".join(messages), fg=THEME["good"])
            if run_after:
                window.after(500, lambda: self.finish_setup_and_launch(window))
        except Exception as e:
            result.config(text=f"Setup option failed:\n{e}", fg=THEME["bad"])

    def finish_setup_and_launch(self, window):
        try:
            self.launch_new_sounddeck_instance()
        except Exception as e:
            messagebox.showerror("Launch Error", str(e))
        window.destroy()

    def recheck_setup_wizard(self, status, result=None):
        self.refresh_devices()
        idx, name = find_vb_cable_relay_output()
        if idx is None:
            status.config(text="VB-Cable is still not detected. A reboot is usually required after installing.", fg=THEME["bad"])
            if result:
                result.config(text="VB-Cable was not found yet.", fg=THEME["bad"])
        else:
            status.config(text=f"VB-Cable is installed and ready: {name}", fg=THEME["good"])
            if result:
                result.config(text="VB-Cable detected successfully.", fg=THEME["good"])
            self.vb_error_shown = False

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
            self.master_limiter_var.get()
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
        ffmpeg = find_bundled_ffmpeg()
        if ffmpeg:
            messagebox.showinfo("FFmpeg", f"FFmpeg found:\n{ffmpeg}")
        else:
            messagebox.showerror("FFmpeg", "FFmpeg was not found.")

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
        self.refresh_favorites()
        self.refresh_recent()

    def refresh_list_only(self):
        self.visible = self.lib.search(self.search_entry.get())
        self.library_list.delete(0, tk.END)
        for path in self.visible:
            self.library_list.insert(tk.END, self.lib.display_name(path))

    def refresh_favorites(self):
        self.fav_list.delete(0, tk.END)
        for path in self.cfg.data.get("favorites", []):
            if os.path.exists(path):
                self.fav_list.insert(tk.END, Path(path).name)

    def refresh_recent(self):
        self.recent_list.delete(0, tk.END)
        for path in self.cfg.data.get("recent", []):
            if os.path.exists(path):
                self.recent_list.insert(tk.END, Path(path).name)

    def get_selected_library_path(self):
        selected = self.library_list.curselection()
        if not selected:
            return None
        idx = selected[0]
        if idx < 0 or idx >= len(self.visible):
            return None
        return self.visible[idx]

    def settings_for(self, path):
        return self.cfg.sound_settings(path)

    def decoded_for(self, path):
        return decode_audio_file(path, self.settings_for(path), self.cfg.data.get("normalize_audio", False))

    def play_path(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            data = self.decoded_for(path)
            self.mixer.load(path, data)
            self.mixer.play()
            self.cfg.add_recent(path)
            self.now_label.config(text=f"Playing: {Path(path).name}")
            self.refresh_recent()
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def play_overlap_path(self, path):
        if not path or not os.path.exists(path):
            return
        if not self.mixer.primary_active:
            self.play_path(path)
            return
        try:
            settings = self.settings_for(path)
            data = self.decoded_for(path)
            self.mixer.play_layer(path, data, volume=float(settings.get("volume", 1.0)), loop=bool(settings.get("loop", False)))
            self.cfg.add_recent(path)
            self.refresh_recent()
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def smart_play_path(self, path):
        if self.allow_overlap_var.get() and self.mixer.primary_active:
            self.play_overlap_path(path)
        else:
            self.play_path(path)

    def library_double_click(self, event=None):
        self.smart_play_path(self.get_selected_library_path())

    def play_selected_file(self):
        self.play_path(self.get_selected_library_path())

    def play_selected_overlap(self):
        self.play_overlap_path(self.get_selected_library_path())

    def play_listbox_path(self, listbox, paths):
        selected = listbox.curselection()
        if selected:
            path = paths[selected[0]]
            self.smart_play_path(path)

    def library_right_click(self, event):
        nearest = self.library_list.nearest(event.y)
        if nearest >= 0:
            self.library_list.selection_clear(0, tk.END)
            self.library_list.selection_set(nearest)
        path = self.get_selected_library_path()
        if not path:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Play", command=lambda: self.play_path(path))
        menu.add_command(label="Play Overlap", command=lambda: self.play_overlap_path(path))
        menu.add_command(label="Add to Queue", command=lambda: self.add_path_to_queue(path))
        menu.add_command(label="Favorite/Unfavorite", command=lambda: self.toggle_favorite(path))
        menu.add_command(label="Edit Tags", command=lambda: self.edit_tags(path))
        menu.add_command(label="Sound Settings", command=lambda: self.edit_sound_settings(path))
        menu.add_command(label="Pin to Grid", command=lambda: self.pin_to_grid(path))
        menu.tk_popup(event.x_root, event.y_root)

    def add_path_to_queue(self, path):
        if path:
            self.queue.append(path)
            self.queue_list.insert(tk.END, Path(path).name)

    def add_selected_to_queue(self):
        self.add_path_to_queue(self.get_selected_library_path())

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

    def play_queue_selected(self):
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
        self.mixer.restart()

    def stop(self):
        self.mixer.stop()
        self.now_label.config(text="Stopped")

    def stop_overlaps(self):
        self.mixer.stop_layers()

    def stop_all(self):
        self.mixer.stop_all()
        self.now_label.config(text="Stopped all sounds")

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
        self.cfg.data["allow_overlap"] = bool(self.allow_overlap_var.get())
        self.cfg.data["normalize_audio"] = bool(self.normalize_var.get())
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
                label += " [missing]"
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

    def play_playlist_track(self):
        name = self.playlist_var.get()
        selected = self.playlist_tracks.curselection()
        if not name or not selected:
            return
        tracks = self.cfg.data["playlists"].get(name, [])
        idx = selected[0]
        if 0 <= idx < len(tracks):
            self.smart_play_path(tracks[idx])

    def play_playlist(self):
        name = self.playlist_var.get()
        if not name:
            return
        tracks = [path for path in self.cfg.data["playlists"].get(name, []) if os.path.exists(path)]
        if not tracks:
            messagebox.showinfo("Empty Playlist", "No valid tracks in this playlist.")
            return
        self.clear_queue()
        for path in tracks:
            self.add_path_to_queue(path)
        self.play_queue_index(0)

    def export_playlist(self):
        name = self.playlist_var.get()
        if not name:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = {name: self.cfg.data["playlists"].get(name, [])}
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def import_playlist(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for name, tracks in data.items():
                if isinstance(tracks, list):
                    self.cfg.data["playlists"][name] = tracks
            self.cfg.save()
            self.refresh_playlists()

    def toggle_selected_favorite(self):
        self.toggle_favorite(self.get_selected_library_path())

    def toggle_favorite(self, path):
        if not path:
            return
        favs = self.cfg.data.setdefault("favorites", [])
        if path in favs:
            favs.remove(path)
        else:
            favs.append(path)
        self.cfg.save()
        self.refresh_list_only()
        self.refresh_favorites()
        self.refresh_grid_if_open()

    def edit_selected_tags(self):
        self.edit_tags(self.get_selected_library_path())

    def edit_tags(self, path):
        if not path:
            return
        old = ", ".join(self.cfg.data.setdefault("tags", {}).get(path, []))
        new = simpledialog.askstring("Edit Tags", "Comma-separated tags:", initialvalue=old)
        if new is None:
            return
        tags = [x.strip() for x in new.split(",") if x.strip()]
        self.cfg.data["tags"][path] = tags
        self.cfg.save()
        self.refresh_list_only()

    def edit_selected_sound_settings(self):
        self.edit_sound_settings(self.get_selected_library_path())

    def edit_sound_settings(self, path):
        if not path:
            return
        settings = self.settings_for(path)
        win = tk.Toplevel(self.root)
        win.title(f"Sound Settings - {Path(path).name}")
        win.configure(bg=THEME["panel"])
        fields = {}
        rows = [
            ("Volume", "volume"),
            ("Fade in ms", "fade_in_ms"),
            ("Fade out ms", "fade_out_ms"),
            ("Trim start ms", "trim_start_ms"),
            ("Trim end ms", "trim_end_ms"),
            ("Hotkey", "hotkey")
        ]
        for r, (label, key) in enumerate(rows):
            tk.Label(win, text=label, bg=THEME["panel"], fg=THEME["text"]).grid(row=r, column=0, sticky="w", padx=8, pady=4)
            var = tk.StringVar(value=str(settings.get(key, "")))
            tk.Entry(win, textvariable=var, bg=THEME["panel2"], fg=THEME["text"], insertbackground=THEME["text"]).grid(row=r, column=1, sticky="ew", padx=8, pady=4)
            fields[key] = var
        loop_var = tk.BooleanVar(value=bool(settings.get("loop", False)))
        tk.Checkbutton(win, text="Loop when played as overlap/grid sound", variable=loop_var, bg=THEME["panel"], fg=THEME["text"], selectcolor=THEME["panel2"]).grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=8, pady=4)
        def save():
            try:
                settings["volume"] = float(fields["volume"].get() or 1.0)
                settings["fade_in_ms"] = int(float(fields["fade_in_ms"].get() or 0))
                settings["fade_out_ms"] = int(float(fields["fade_out_ms"].get() or 0))
                settings["trim_start_ms"] = int(float(fields["trim_start_ms"].get() or 0))
                settings["trim_end_ms"] = int(float(fields["trim_end_ms"].get() or 0))
                settings["hotkey"] = fields["hotkey"].get().strip()
                settings["loop"] = bool(loop_var.get())
                self.cfg.data.setdefault("hotkeys", {})[path] = settings["hotkey"]
                self.cfg.save()
                self.register_hotkeys()
                win.destroy()
            except Exception as e:
                messagebox.showerror("Settings Error", str(e))
        ttk.Button(win, text="Save", command=save).grid(row=len(rows) + 1, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        win.columnconfigure(1, weight=1)

    def pin_selected_to_grid(self):
        self.pin_to_grid(self.get_selected_library_path())

    def pin_to_grid(self, path):
        if not path:
            return
        pins = self.cfg.data.setdefault("grid_pins", [])
        if path not in pins:
            pins.append(path)
        self.cfg.save()
        self.refresh_grid_if_open()

    def open_grid(self):
        if self.grid_window and self.grid_window.winfo_exists():
            self.grid_window.lift()
            return
        self.grid_window = tk.Toplevel(self.root)
        self.grid_window.title("SoundDeck Grid")
        self.grid_window.configure(bg=THEME["bg"])
        self.grid_window.geometry("900x600")
        self.refresh_grid_if_open()

    def refresh_grid_if_open(self):
        if not self.grid_window or not self.grid_window.winfo_exists():
            return
        for child in self.grid_window.winfo_children():
            child.destroy()
        top = tk.Frame(self.grid_window, bg=THEME["bg"])
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="Refresh", command=self.refresh_grid_if_open).pack(side="left")
        ttk.Button(top, text="Use Favorites", command=lambda: self.populate_grid(self.cfg.data.get("favorites", []))).pack(side="left", padx=4)
        ttk.Button(top, text="Use Pins", command=lambda: self.populate_grid(self.cfg.data.get("grid_pins", []))).pack(side="left", padx=4)
        ttk.Button(top, text="Use Visible Library", command=lambda: self.populate_grid(self.visible[:80])).pack(side="left", padx=4)
        self.grid_frame = tk.Frame(self.grid_window, bg=THEME["bg"])
        self.grid_frame.pack(fill="both", expand=True, padx=8, pady=8)
        pins = [p for p in self.cfg.data.get("grid_pins", []) if os.path.exists(p)]
        self.populate_grid(pins if pins else self.cfg.data.get("favorites", []))

    def populate_grid(self, paths):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        paths = [p for p in paths if os.path.exists(p)]
        cols = 4
        for i, path in enumerate(paths):
            btn = tk.Button(
                self.grid_frame,
                text=Path(path).stem[:32],
                bg=THEME["panel2"],
                fg=THEME["text"],
                activebackground=THEME["blue"],
                activeforeground="#ffffff",
                relief="flat",
                wraplength=170,
                command=lambda p=path: self.smart_play_path(p)
            )
            btn.grid(row=i // cols, column=i % cols, sticky="nsew", padx=5, pady=5, ipady=18)
        for c in range(cols):
            self.grid_frame.columnconfigure(c, weight=1)

    def import_config(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.cfg.import_from(path)
            self.refresh_library()
            self.refresh_playlists()
            self.refresh_devices()
            self.register_hotkeys()
            messagebox.showinfo("Import", "Config imported.")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def export_config(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.cfg.export_to(path)
            messagebox.showinfo("Export", "Config exported.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def toggle_global_hotkeys(self):
        self.cfg.data["global_hotkeys"] = bool(self.global_hotkeys_var.get())
        self.cfg.save()
        self.register_hotkeys()

    def register_hotkeys(self):
        self.unregister_hotkeys()
        if not self.cfg.data.get("global_hotkeys", False):
            return
        if keyboard is None:
            messagebox.showwarning("Hotkeys", "The keyboard package is not installed or could not start.")
            return
        for path, hotkey in self.cfg.data.get("hotkeys", {}).items():
            if not hotkey or not os.path.exists(path):
                continue
            try:
                handle = keyboard.add_hotkey(hotkey, lambda p=path: self.root.after(0, lambda: self.smart_play_path(p)))
                self.hotkey_handles.append(handle)
            except Exception:
                pass

    def unregister_hotkeys(self):
        if keyboard is None:
            return
        for handle in self.hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self.hotkey_handles.clear()

    def show_audio_error(self, msg):
        self.now_label.config(text="Audio error")
        messagebox.showerror("Audio Error", msg)

    def tick(self):
        duration = self.mixer.dur_seconds
        position = self.mixer.pos_seconds
        self.time_label.config(text=f"{fmt_time(position)} / {fmt_time(duration)}")
        self.layers_label.config(text=f"{self.mixer.active_layers} overlapping")
        if duration > 0 and not self.dragging_seek:
            self.seek_var.set(max(0, min(100, (position / duration) * 100)))
        if self.mixer.consume_finished():
            self.finished_track()
        self.root.after(200, self.tick)

    def close(self):
        self.unregister_hotkeys()
        self.mixer.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
