import os
import shutil
import subprocess
import sys
import numpy as np
import soundfile as sf
from .constants import SAMPLE_RATE, resource_path, app_dir

def subprocess_flags():
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0

def find_bundled_ffmpeg():
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    candidates = [
        os.path.join(app_dir(), "ffmpeg", exe_name),
        resource_path(os.path.join("ffmpeg", exe_name)),
        os.path.join(app_dir(), "_internal", "ffmpeg", exe_name),
        shutil.which(exe_name)
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None

def decode_with_ffmpeg(path):
    ffmpeg = find_bundled_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg was not found.")
    cmd = [
        ffmpeg,
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
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess_flags()
    )
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"FFmpeg could not decode this file.\n\n{err}")
    audio = np.frombuffer(result.stdout, dtype=np.float32)
    if audio.size < 2:
        raise RuntimeError("Decoded audio was empty.")
    if audio.size % 2 != 0:
        audio = audio[:-1]
    return np.ascontiguousarray(audio.reshape((-1, 2)).copy(), dtype=np.float32)

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

def apply_edits(data, settings, normalize=False):
    if data is None or len(data) == 0:
        return data
    start = max(0, int(float(settings.get("trim_start_ms", 0)) / 1000.0 * SAMPLE_RATE))
    end_trim = max(0, int(float(settings.get("trim_end_ms", 0)) / 1000.0 * SAMPLE_RATE))
    end = len(data) - end_trim if end_trim < len(data) else len(data)
    if start < end:
        data = data[start:end].copy()
    fade_in = max(0, int(float(settings.get("fade_in_ms", 0)) / 1000.0 * SAMPLE_RATE))
    fade_out = max(0, int(float(settings.get("fade_out_ms", 0)) / 1000.0 * SAMPLE_RATE))
    if fade_in > 0 and len(data) > 0:
        n = min(fade_in, len(data))
        curve = np.linspace(0.0, 1.0, n, dtype=np.float32).reshape((-1, 1))
        data[:n] *= curve
    if fade_out > 0 and len(data) > 0:
        n = min(fade_out, len(data))
        curve = np.linspace(1.0, 0.0, n, dtype=np.float32).reshape((-1, 1))
        data[-n:] *= curve
    if normalize and len(data) > 0:
        peak = float(np.max(np.abs(data)))
        if peak > 0.0:
            data = data * min(1.0 / peak * 0.92, 4.0)
    return np.ascontiguousarray(np.clip(data, -1.0, 1.0), dtype=np.float32)

def decode_audio_file(path, settings=None, normalize=False):
    settings = settings or {}
    try:
        data = decode_with_ffmpeg(path)
    except Exception:
        data, rate = sf.read(path, dtype="float32", always_2d=True)
        data = to_stereo_float32(data)
        data = resample_linear(data, rate, SAMPLE_RATE)
    return apply_edits(data, settings, normalize=normalize)
