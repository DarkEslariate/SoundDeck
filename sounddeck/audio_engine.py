import threading
from collections import deque
import numpy as np
import sounddevice as sd
from .constants import SAMPLE_RATE, CHANNELS, CHUNK
from .devices import output_channels_supported, input_channels_supported, find_vb_cable_relay_output

def clip_audio(data):
    return np.clip(data, -1.0, 1.0).astype(np.float32, copy=False)

def soft_limit(data):
    return np.tanh(np.clip(data, -3.0, 3.0)).astype(np.float32, copy=False)

def to_stereo_float32(data):
    data = np.asarray(data, dtype=np.float32)
    if data.ndim == 1:
        data = data.reshape((-1, 1))
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]
    return np.ascontiguousarray(data, dtype=np.float32)

def write_mix_to_outdata(outdata, mix):
    if outdata.shape[1] == 1:
        outdata[:, 0] = np.mean(mix, axis=1)
    else:
        outdata[:, :2] = mix[:, :2]

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
        self.master_limiter = bool(cfg.data.get("master_limiter", True))
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
        self.layers = []
        self.next_layer_id = 1
        self.finished_pending = False
        self.on_error = None
        self.restart_streams()

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
        relay_device, _ = self.auto_select_relay_device()
        if relay_device is not None:
            relay_channels = output_channels_supported(relay_device)
            if relay_channels is not None:
                try:
                    relay_stream = sd.OutputStream(
                        samplerate=SAMPLE_RATE,
                        channels=relay_channels,
                        dtype="float32",
                        device=relay_device,
                        blocksize=CHUNK,
                        callback=lambda outdata, frames, time_info, status, g=gen: self._relay_callback(g, outdata, frames, time_info, status),
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
            if monitor_channels is not None:
                try:
                    monitor_stream = sd.OutputStream(
                        samplerate=SAMPLE_RATE,
                        channels=monitor_channels,
                        dtype="float32",
                        device=self.monitor_device,
                        blocksize=CHUNK,
                        callback=lambda outdata, frames, time_info, status, g=gen: self._monitor_callback(g, outdata, frames, time_info, status),
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
            if input_channels_supported(self.mic_device) is not None:
                try:
                    mic_stream = sd.InputStream(
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        dtype="float32",
                        device=self.mic_device,
                        blocksize=CHUNK,
                        callback=lambda indata, frames, time_info, status, g=gen: self._mic_callback(g, indata, frames, time_info, status),
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

    def _primary_chunk(self, frames):
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

    def _layers_chunk(self, frames):
        mix = np.zeros((frames, 2), dtype=np.float32)
        active = []
        for layer in self.layers:
            if layer.get("paused"):
                active.append(layer)
                continue
            audio = layer["audio"]
            frame = int(layer["frame"])
            total = int(layer["total"])
            if frame >= total:
                if layer.get("loop"):
                    frame = 0
                else:
                    continue
            end = min(frame + frames, total)
            chunk = audio[frame:end]
            if len(chunk):
                mix[:len(chunk)] += chunk * float(layer.get("volume", 1.0))
            frame = end
            if frame >= total and layer.get("loop"):
                remain = frames - len(chunk)
                if remain > 0:
                    take = min(remain, total)
                    mix[len(chunk):len(chunk) + take] += audio[:take] * float(layer.get("volume", 1.0))
                    frame = take
            layer["frame"] = frame
            if layer["frame"] < total or layer.get("loop"):
                active.append(layer)
        self.layers = active
        return mix

    def _relay_callback(self, gen, outdata, frames, time_info, status):
        outdata.fill(0)
        try:
            with self.lock:
                if gen != self.generation:
                    raise sd.CallbackStop
                sound, ended_now = self._primary_chunk(frames)
                layers = self._layers_chunk(frames)
                mic = self._pop_from_queue(self.mic_queue, frames)
                relay_mix = (sound * self.volume) + layers
                monitor_mix = np.zeros((frames, 2), dtype=np.float32)
                if self.mic_passthrough:
                    relay_mix += mic * self.mic_volume
                if self.monitor_sound:
                    monitor_mix += (sound * self.volume) + layers
                if self.monitor_mic:
                    monitor_mix += mic * self.mic_volume
                monitor_mix *= self.monitor_volume
                if self.monitor_stream:
                    self.monitor_queue.append(self._limit(monitor_mix))
                    while len(self.monitor_queue) > self.max_queue_chunks:
                        self.monitor_queue.popleft()
                write_mix_to_outdata(outdata, self._limit(relay_mix))
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
                write_mix_to_outdata(outdata, self._limit(data))
        except sd.CallbackStop:
            raise
        except Exception:
            outdata.fill(0)

    def _limit(self, data):
        if self.master_limiter:
            return soft_limit(data)
        return clip_audio(data)

    def consume_finished(self):
        with self.lock:
            if self.finished_pending:
                self.finished_pending = False
                return True
        return False

    def load(self, path, audio):
        with self.lock:
            self.file = path
            self.audio = audio
            self.frame = 0
            self.total = int(len(audio))
            self.playing = False
            self.paused = False
            self.finished_pending = False
            self.monitor_queue.clear()

    def play_layer(self, path, audio, volume=1.0, loop=False):
        with self.lock:
            limit = max(1, int(self.cfg.data.get("overlap_limit", 8)))
            while len(self.layers) >= limit:
                self.layers.pop(0)
            layer_id = self.next_layer_id
            self.next_layer_id += 1
            self.layers.append({
                "id": layer_id,
                "path": path,
                "audio": audio,
                "frame": 0,
                "total": int(len(audio)),
                "volume": float(volume),
                "loop": bool(loop),
                "paused": False
            })
            return layer_id

    def stop_layers(self):
        with self.lock:
            self.layers.clear()

    def stop_all(self):
        with self.lock:
            self.playing = False
            self.paused = False
            self.frame = 0
            self.layers.clear()
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

    def set_toggles(self, mic_passthrough, monitor_sound, monitor_mic, master_limiter=None):
        with self.lock:
            self.mic_passthrough = bool(mic_passthrough)
            self.monitor_sound = bool(monitor_sound)
            self.monitor_mic = bool(monitor_mic)
            if master_limiter is not None:
                self.master_limiter = bool(master_limiter)
            self.cfg.data["mic_passthrough"] = self.mic_passthrough
            self.cfg.data["monitor_sound"] = self.monitor_sound
            self.cfg.data["monitor_mic"] = self.monitor_mic
            self.cfg.data["master_limiter"] = self.master_limiter
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

    @property
    def primary_active(self):
        with self.lock:
            return self.audio is not None and self.playing and self.total > 0 and self.frame < self.total

    @property
    def active_layers(self):
        with self.lock:
            return len(self.layers)
