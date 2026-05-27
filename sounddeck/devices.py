import sounddevice as sd

def output_channels_supported(device):
    for channels in (2, 1):
        try:
            sd.check_output_settings(
                device=device,
                samplerate=48000,
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
            samplerate=48000,
            channels=1,
            dtype="float32",
        )
        return 1
    except Exception:
        return None

def is_vb_cable_playback_name(name):
    lowered = str(name).lower()
    if "cable input" in lowered:
        return True
    if "vb-audio" in lowered and "cable" in lowered and "input" in lowered:
        return True
    return False

def find_vb_cable_relay_output():
    try:
        devices = sd.query_devices()
    except Exception:
        return None, None
    for i, dev in enumerate(devices):
        name = dev.get("name", f"Device {i}")
        if dev.get("max_output_channels", 0) <= 0:
            continue
        if output_channels_supported(i) is None:
            continue
        if is_vb_cable_playback_name(name):
            return i, name
    return None, None

def list_output_devices():
    outputs = {}
    if output_channels_supported(None) is not None:
        outputs["System default"] = None
    try:
        for i, dev in enumerate(sd.query_devices()):
            name = dev.get("name", f"Device {i}")
            if dev.get("max_output_channels", 0) > 0 and output_channels_supported(i) is not None:
                outputs[f"{i}: {name}"] = i
    except Exception:
        pass
    return outputs

def list_input_devices():
    inputs = {"No microphone": "none"}
    if input_channels_supported(None) is not None:
        inputs["System default"] = None
    try:
        for i, dev in enumerate(sd.query_devices()):
            name = dev.get("name", f"Device {i}")
            if dev.get("max_input_channels", 0) > 0 and input_channels_supported(i) is not None:
                inputs[f"{i}: {name}"] = i
    except Exception:
        pass
    return inputs
