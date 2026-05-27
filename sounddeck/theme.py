import tkinter as tk
from tkinter import ttk

THEME = {}

def set_theme(mode):
    mode = "light" if str(mode).lower() == "light" else "dark"
    if mode == "light":
        values = {
            "mode": "light",
            "bg": "#cfe5ff",
            "panel": "#ffffff",
            "panel2": "#e3f0ff",
            "card": "#bddcff",
            "blue": "#1e88ff",
            "blue2": "#0f6fd6",
            "text": "#142033",
            "muted": "#4e647d",
            "border": "#3f9bff",
            "good": "#128847",
            "bad": "#c73754",
            "warn": "#a87800",
            "scale_trough": "#b7d8ff",
            "scale_bg": "#e3f0ff",
            "tab_selected": "#ffffff",
            "tab_idle": "#d7eaff"
        }
    else:
        values = {
            "mode": "dark",
            "bg": "#0c1a2b",
            "panel": "#000000",
            "panel2": "#111111",
            "card": "#1b1b1b",
            "blue": "#1e88ff",
            "blue2": "#58a6ff",
            "text": "#e7f1ff",
            "muted": "#9fb4cf",
            "border": "#2f65a0",
            "good": "#42d392",
            "bad": "#ff5c7a",
            "warn": "#f5c542",
            "scale_trough": "#1d3a5a",
            "scale_bg": "#111111",
            "tab_selected": "#000000",
            "tab_idle": "#111111"
        }
    THEME.clear()
    THEME.update(values)

def apply_theme(root, mode="dark"):
    set_theme(mode)
    root.configure(bg=THEME["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(".", font=("Segoe UI", 10))
    style.configure("TFrame", background=THEME["bg"])
    style.configure("Panel.TFrame", background=THEME["panel"])
    style.configure("TLabel", background=THEME["panel"], foreground=THEME["text"])
    style.configure("Muted.TLabel", background=THEME["panel"], foreground=THEME["muted"])
    style.configure("TLabelframe", background=THEME["panel"], foreground=THEME["text"], bordercolor=THEME["border"], lightcolor=THEME["border"], darkcolor=THEME["border"])
    style.configure("TLabelframe.Label", background=THEME["bg"], foreground=THEME["blue2"], font=("Segoe UI", 10, "bold"))
    style.configure("TButton", background=THEME["panel2"], foreground=THEME["text"], borderwidth=0, focusthickness=0, padding=(10, 5))
    style.map("TButton", background=[("active", THEME["card"]), ("pressed", THEME["blue"])], foreground=[("active", THEME["text"]), ("pressed", "#ffffff")])
    style.configure("TCheckbutton", background=THEME["panel"], foreground=THEME["text"], focuscolor=THEME["panel"], padding=(4, 2))
    style.map("TCheckbutton", background=[("active", THEME["panel"])], foreground=[("active", THEME["blue2"])])
    style.configure("TEntry", fieldbackground=THEME["panel2"], background=THEME["panel2"], foreground=THEME["text"], insertcolor=THEME["text"], bordercolor=THEME["border"], lightcolor=THEME["border"], darkcolor=THEME["border"])
    style.configure("TCombobox", fieldbackground=THEME["panel2"], background=THEME["panel2"], foreground=THEME["text"], arrowcolor=THEME["blue2"], bordercolor=THEME["border"], lightcolor=THEME["border"], darkcolor=THEME["border"])
    style.map("TCombobox", fieldbackground=[("readonly", THEME["panel2"])], foreground=[("readonly", THEME["text"])], selectbackground=[("readonly", THEME["panel2"])], selectforeground=[("readonly", THEME["text"])])
    style.configure("Horizontal.TScale", background=THEME["panel"], troughcolor=THEME["scale_trough"], bordercolor=THEME["panel"], lightcolor=THEME["blue"], darkcolor=THEME["blue"])
    style.map("Horizontal.TScale", background=[("active", THEME["panel"])], troughcolor=[("active", THEME["scale_trough"])])
    style.configure("TNotebook", background=THEME["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background=THEME["tab_idle"], foreground=THEME["text"], padding=(12, 6), bordercolor=THEME["border"], lightcolor=THEME["border"], darkcolor=THEME["border"])
    style.map("TNotebook.Tab", background=[("selected", THEME["tab_selected"]), ("active", THEME["card"])], foreground=[("selected", THEME["text"]), ("active", THEME["text"])])
    root.option_add("*TCombobox*Listbox.background", THEME["panel2"])
    root.option_add("*TCombobox*Listbox.foreground", THEME["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", THEME["blue"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

def style_listbox(widget):
    widget.configure(
        bg=THEME["panel"],
        fg=THEME["text"],
        selectbackground=THEME["blue"],
        selectforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=THEME["border"],
        highlightcolor=THEME["blue"],
        activestyle="none",
        font=("Segoe UI", 10)
    )

def style_label(widget, kind="normal"):
    fg = THEME["text"]
    if kind == "muted":
        fg = THEME["muted"]
    if kind == "good":
        fg = THEME["good"]
    if kind == "bad":
        fg = THEME["bad"]
    if kind == "warn":
        fg = THEME["warn"]
    widget.configure(bg=THEME["panel"], fg=fg)
