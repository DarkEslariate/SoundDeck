# SoundDeck

**SoundDeck** is an ultra-lightweight local Windows soundboard app that routes audio through **VB-Audio Virtual Cable**, making it easy to play sounds into apps like Discord, OBS, games, voice chats, and recording software.

It was built as a free alternative to subscription-based PC soundboard apps, with support for local audio files, playlists, queue playback, mic passthrough, local monitoring, loop options, themes, and FFmpeg-powered decoding, while keeping system resource usage low for gaming, streaming, recording, and everyday use.

---

## Features

- Local soundboard playback
- Automatic VB-Cable relay detection
- Discord/OBS microphone routing
- Optional microphone passthrough
- Optional local soundboard monitoring
- Optional mic monitoring
- Multiple audio folders
- Searchable audio library
- Queue system
- Playlists
- Autoplay next track
- Loop current song
- Loop playlist
- Dark and light themes
- FFmpeg decoding support
- Portable Windows build through PyInstaller

---

## Supported Audio Formats

SoundDeck supports the following audio formats:

- FLAC
- WAV
- AIFF
- OGG
- MP3
- M4A
- AAC
- WMA
- OPUS
- WEBM
- MP4 audio
- CAF
- MKA

---

## Requirements

### For Users

To use the finished portable release, users only need:

- Windows
- VB-Audio Virtual Cable, for Discord/OBS/voice-chat routing

Python and FFmpeg are **not required** for users running an official release ZIP, because the release build includes the bundled app files.

### For Developers

To build SoundDeck from source, you need:

- Python
- FFmpeg binaries
- Python packages listed in `requirements.txt`

Install the Python dependencies with:

```bat
python -m pip install -r requirements.txt
```

---

## FFmpeg Binaries

FFmpeg binaries are **not included in this source repository**.

SoundDeck uses FFmpeg to decode common audio formats such as MP3, M4A, AAC, WMA, OPUS, WEBM, and MP4 audio. To build SoundDeck from source, you need to provide your own FFmpeg binaries.

Create a folder named `ffmpeg` in the project directory:

```text
SoundDeck
└─ ffmpeg
   ├─ ffmpeg.exe
   └─ ffprobe.exe
```

You can download FFmpeg from:

```text
https://ffmpeg.org/download.html
```

After downloading FFmpeg, copy these two files into the `ffmpeg` folder:

```text
ffmpeg.exe
ffprobe.exe
```

The build script expects them here:

```text
ffmpeg\ffmpeg.exe
ffmpeg\ffprobe.exe
```

If those files are missing, `build_release.bat` will stop and show an error.

### Release Builds

Official release ZIPs may include FFmpeg binaries inside the bundled app so users do not need to install FFmpeg manually.

FFmpeg is not owned by this project and is distributed under its own license terms. See:

```text
licenses/FFMPEG_NOTICE.txt
```

and:

```text
https://ffmpeg.org/legal.html
```

---

## First-Run Setup Wizard

SoundDeck includes a setup wizard that checks whether VB-Audio Virtual Cable is installed.

If VB-Cable is missing, the wizard can open the official VB-Audio download page and show the required install steps. VB-Cable is not bundled with this source repository or silently installed by SoundDeck.

The setup wizard can also create a desktop shortcut, create a Windows startup shortcut, and launch SoundDeck after the wizard closes.

VB-Cable installation requires administrator permission and usually requires a PC restart before SoundDeck can detect it.

---

## VB-Audio Virtual Cable Setup

SoundDeck uses VB-Audio Virtual Cable to send soundboard audio into apps as a microphone source.

Install VB-Audio Virtual Cable from:

```text
https://vb-audio.com/Cable/
```

After installing it, restart your PC.

SoundDeck automatically looks for VB-Cable’s playback device, usually named:

```text
CABLE Input (VB-Audio Virtual Cable)
```

Apps like Discord or OBS should listen to:

```text
CABLE Output
```

---

## Recommended Audio Setup

Use this setup for the cleanest routing:

```text
Windows default output        = Your headphones/speakers
Browser/YouTube/game output   = Your headphones/speakers
Discord/OBS microphone input  = CABLE Output
SoundDeck microphone input    = Your headset microphone
SoundDeck monitor output      = Your headphones/speakers
```

This prevents your desktop audio from being sent into Discord/OBS.

---

## How SoundDeck Routing Works

SoundDeck automatically sends soundboard audio to VB-Cable.

You do **not** need to manually choose the relay output. If VB-Cable is installed correctly, SoundDeck will detect it automatically.

Inside Discord, OBS, or another app, set your microphone/input device to:

```text
CABLE Output
```

Then SoundDeck can send audio into that app.

---

## SoundDeck Controls

### Audio Library

Add one or more folders containing audio files. SoundDeck will scan those folders and merge all supported files into one library.

### Queue

Add sounds to the queue and play them in order.

### Playlists

Create playlists inside the app and add selected sounds to them.

### Playback Options

- **Autoplay next**  
  Automatically plays the next item in the queue.

- **Loop song**  
  Repeats the currently playing sound.

- **Loop playlist**  
  Restarts the queue or playlist after the final item finishes.

### Routing Options

- **Send mic to apps**  
  Sends your selected microphone into Discord/OBS along with soundboard audio.

- **Hear soundboard**  
  Lets you hear SoundDeck sounds locally through your monitor output.

- **Hear yourself**  
  Lets you hear your selected microphone locally. This may have a slight delay.

---

## Building From Source

Your project folder should look like this:

```text
SoundDeck
├─ SoundDeck.py
├─ build_release.bat
├─ requirements.txt
├─ README.md
├─ LICENSE
├─ VERSION.txt
├─ sounddeck_config.example.json
├─ assets
│  ├─ SoundDeck.ico
│  └─ SoundDeck.png
├─ licenses
│  └─ FFMPEG_NOTICE.txt
└─ ffmpeg
   ├─ ffmpeg.exe      # Not included in source repo
   └─ ffprobe.exe     # Not included in source repo
```

Then run:

```bat
build_release.bat
```

After the build finishes, the portable app will be created at:

```text
dist\SoundDeck
```

Zip the `SoundDeck` folder inside `dist` when sharing the app.

---

## Release ZIP Structure

A release ZIP should contain the full portable app folder, not just the EXE.

Example:

```text
SoundDeck
├─ SoundDeck.exe
├─ README.md
├─ LICENSE
├─ VERSION.txt
├─ sounddeck_config.json
├─ SoundDeck.ico
├─ licenses
│  └─ FFMPEG_NOTICE.txt
└─ _internal
   ├─ ffmpeg
   │  ├─ ffmpeg.exe
   │  └─ ffprobe.exe
   └─ other bundled app files
```

Do **not** delete the `_internal` folder. The EXE needs it to run.

---

## Troubleshooting

### SoundDeck says VB-Cable was not found

Install VB-Audio Virtual Cable, restart your PC, then reopen SoundDeck.

Make sure Windows shows devices named something like:

```text
CABLE Input
CABLE Output
```

### Discord or OBS cannot hear SoundDeck

In Discord, OBS, or your voice app, set the microphone/input device to:

```text
CABLE Output
```

### Desktop audio is being sent into Discord/OBS

This usually means Windows or an app is outputting desktop audio into VB-Cable.

Check:

```text
Windows Settings > System > Sound > Volume mixer
```

Make sure your browser, game, or media player is **not** outputting to:

```text
CABLE Input
```

Your normal apps should output to your headphones/speakers.

### I cannot hear SoundDeck locally

Enable:

```text
Hear soundboard
```

Then set Monitor Output to your headphones or speakers.

---

## Versioning

SoundDeck uses semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
1.0.0 = first stable release
1.0.1 = bug fix
1.1.0 = new feature
2.0.0 = major rewrite or breaking change
```

---

## FFmpeg Notice

SoundDeck release builds may include FFmpeg binaries for decoding audio files.

FFmpeg is a free and open-source multimedia project. FFmpeg has its own license terms depending on the specific build used.

FFmpeg project:

```text
https://ffmpeg.org/
```

FFmpeg legal information:

```text
https://ffmpeg.org/legal.html
```

---

## License

SoundDeck’s source code is licensed under the license included in this repository.

FFmpeg is not owned by this project and is distributed under its own license terms.

---

## Disclaimer

SoundDeck is not affiliated with VB-Audio, Discord, OBS, or FFmpeg.

VB-Audio Virtual Cable is required for microphone-style routing into other applications.

## v1.1 Alpha Features

- Modular Python package structure
- Overlapping multi-sound playback
- Grid Mode
- Favorites
- Grid pins
- Per-sound volume
- Per-sound loop for overlap/grid playback
- Per-sound fade in and fade out
- Per-sound start and end trim
- Tags and tag-aware search
- Recent sounds
- Optional global hotkeys
- Playlist import and export
- Full config import and export
- Optional audio normalization
- Master limiter
- Stop Overlaps and Stop All controls

