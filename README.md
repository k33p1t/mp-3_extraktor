# HoloAudio

A futuristic holographic-style desktop application that combines:

- Video → Audio extractor (MP3 / AAC)
- Media Player (VLC-powered) with spectrum visualizer
- YouTube integration (login, search, playlists, liked videos)
- Spotify integration (login, search, 30s previews)
- Network discovery (non-aggressive ping sweep + Graphviz topology)

Designed with a dark cyan holographic UI inspired by sci-fi dashboards.

---

## Features

- **Extractor** – Convert video to MP3 or AAC with progress bar and bitrate selection
- **Player** – Clean Now Playing interface + real-time spectrum visualizer
- **YouTube** – OAuth login, search, playlists, thumbnails, play via VLC
- **Spotify** – OAuth login, track search, preview playback
- **Network** – Safe local subnet ping sweep + Graphviz network diagram

---

## Requirements

- Python 3.10+
- VLC media player installed on your system
- Graphviz system package (for topology diagrams)
- Nmap (optional – for enhanced host discovery)

### System Dependencies

**Windows**
- Install [VLC](https://www.videolan.org/)
- Install [Graphviz](https://graphviz.org/download/) and add to PATH
- (Optional) Install [Nmap](https://nmap.org/)

**macOS**
```bash
brew install vlc graphviz nmap