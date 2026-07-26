# HoloAudio

A futuristic holographic-style desktop application built with CustomTkinter.

**Features:**
- Video → Audio Extractor (MP3 / AAC)
- Media Player with VLC + real-time spectrum visualizer
- YouTube integration (OAuth login, search, playlists, thumbnails)
- Spotify integration (OAuth login, search, 30-second previews)
- Network Discovery (non-aggressive local subnet ping sweep + Graphviz topology diagrams)

Designed with a dark cyan holographic UI inspired by sci-fi dashboards.

---

## Screenshots

> Add your own screenshots here after running the app.

---

## Requirements

- Python 3.10 or higher
- VLC Media Player installed on your system
- Graphviz system package (for network diagrams)

### System Dependencies

**Windows**
- [VLC](https://www.videolan.org/)
- [Graphviz](https://graphviz.org/download/) (add to PATH)
- (Optional) [Nmap](https://nmap.org/)

**macOS**
```bash
brew install vlc graphviz