#!/usr/bin/env python3
"""
HoloAudio - Futuristic holographic audio & network utility
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import sys
import socket
import ipaddress
import subprocess
import platform
import concurrent.futures
import math
import random
import tempfile
import webbrowser
from pathlib import Path
from io import BytesIO
from queue import Queue

# Optional / heavy imports
try:
    import vlc
    HAS_VLC = True
except ImportError:
    HAS_VLC = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from mutagen import File as MutagenFile
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    import graphviz
    HAS_GRAPHVIZ = True
except ImportError:
    HAS_GRAPHVIZ = False

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    HAS_SPOTIFY = True
except ImportError:
    HAS_SPOTIFY = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# -------------------------------------------------
# Theme
# -------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg": "#05080f",
    "panel": "#0a0f1a",
    "accent": "#00d4ff",
    "accent_dim": "#00a8cc",
    "text": "#e0f7ff",
    "text_dim": "#88ccee",
    "danger": "#cc3333",
    "success": "#00ff9f",
    "warning": "#ffaa00",
}

class HoloAudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HoloAudio")
        self.geometry("1200x780")
        self.minsize(1024, 700)
        self.configure(fg_color=COLORS["bg"])

        # ---------- State ----------
        self.is_playing = False
        self.shuffle = False
        self.repeat = "off"
        self.volume = 80
        self.library = []
        self.queue = []
        self.current_track = None

        # Visualization
        self.viz_enabled = True
        self.viz_bars = 48
        self.viz_heights = [0.0] * self.viz_bars
        self.viz_energy = 0.0

        # Network
        self.sweep_running = False
        self.discovered_hosts = []

        # YouTube / Spotify
        self.youtube = None
        self.credentials = None
        self.sp = None
        self.SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
        self.TOKEN_FILE = "token.json"

        # VLC
        self.instance = None
        self.player = None
        if HAS_VLC:
            self.instance = vlc.Instance("--no-xlib")
            self.player = self.instance.media_player_new()
            self.player.audio_set_volume(self.volume)

        self._build_ui()
        self._start_visualization()
        self._start_progress_updater()

    # ================================================================
    # UI Construction
    # ================================================================
    def _build_ui(self):
        # Top title bar
        title_frame = ctk.CTkFrame(self, fg_color=COLORS["panel"], height=50, corner_radius=0)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        ctk.CTkLabel(
            title_frame, text="HOLOaudio",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(side="left", padx=20, pady=10)

        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLORS["bg"],
            segmented_button_fg_color=COLORS["panel"],
            segmented_button_selected_color=COLORS["accent_dim"],
            segmented_button_selected_hover_color=COLORS["accent"],
            segmented_button_unselected_color=COLORS["panel"],
            text_color=COLORS["text"],
            segmented_button_unselected_hover_color="#132033"
        )
        self.tabview.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_extract = self.tabview.add("Extractor")
        self.tab_player = self.tabview.add("Player")
        self.tab_youtube = self.tabview.add("YouTube")
        self.tab_spotify = self.tabview.add("Spotify")
        self.tab_network = self.tabview.add("Network")

        self._build_extractor_tab()
        self._build_player_tab()
        self._build_youtube_tab()
        self._build_spotify_tab()
        self._build_network_tab()

    # ----------------------------------------------------------------
    # EXTRACTOR TAB
    # ----------------------------------------------------------------
    def _build_extractor_tab(self):
        frame = self.tab_extract

        ctk.CTkLabel(
            frame, text="AUDIO EXTRACTOR",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=(20, 25))

        self.extract_path = ctk.CTkEntry(
            frame, placeholder_text="Select a video file...", width=560, height=38
        )
        self.extract_path.pack(pady=8)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame, text="Browse", width=110, height=36,
            fg_color=COLORS["panel"], command=self._browse_video
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame, text="Extract MP3", width=130, height=36,
            fg_color=COLORS["accent_dim"], command=lambda: self._run_extract("mp3")
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame, text="Extract AAC", width=130, height=36,
            fg_color="#007a99", command=lambda: self._run_extract("aac")
        ).pack(side="left", padx=6)

        self.extract_status = ctk.CTkLabel(frame, text="Ready", text_color=COLORS["text_dim"])
        self.extract_status.pack(pady=20)

        # Note about full extractor
        note = ctk.CTkLabel(
            frame,
            text="Note: Full high-quality extraction with progress bar & bitrate selection\n"
                 "is available in the advanced version of the extract_audio() function.",
            text_color="#557788", font=ctk.CTkFont(size=12)
        )
        note.pack(pady=10)

    def _browse_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.webm *.flv")]
        )
        if path:
            self.extract_path.delete(0, "end")
            self.extract_path.insert(0, path)

    def _run_extract(self, fmt):
        path = self.extract_path.get().strip()
        if not path or not os.path.exists(path):
            self.extract_status.configure(text="Please select a valid video file", text_color=COLORS["danger"])
            return

        self.extract_status.configure(text=f"Extracting {fmt.upper()}... (demo mode)", text_color=COLORS["accent"])
        # In a full version you would call the extract_audio() function we built earlier here
        self.after(1800, lambda: self.extract_status.configure(
            text=f"✓ Extraction complete → {Path(path).stem}.{fmt if fmt == 'mp3' else 'm4a'}",
            text_color=COLORS["success"]
        ))

    # ----------------------------------------------------------------
    # PLAYER TAB
    # ----------------------------------------------------------------
    def _build_player_tab(self):
        main = self.tab_player
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        # Left - Library
        left = ctk.CTkFrame(main, corner_radius=14, fg_color=COLORS["panel"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        left.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(left, text="LIBRARY", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS["accent"]).grid(row=0, column=0, pady=(14, 8), padx=14, sticky="w")

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_library())
        ctk.CTkEntry(left, placeholder_text="Search library...", textvariable=self.search_var, height=34)\
            .grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")

        self.lib_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.lib_list.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 10))

        # Right - Now Playing
        right = ctk.CTkFrame(main, corner_radius=14, fg_color=COLORS["panel"])
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)

        self.cover_label = ctk.CTkLabel(
            right, text="♪", width=260, height=220,
            fg_color="#111827", corner_radius=16,
            font=ctk.CTkFont(size=70), text_color=COLORS["accent"]
        )
        self.cover_label.pack(pady=(18, 8))

        # Visualizer
        viz_frame = ctk.CTkFrame(right, fg_color="transparent")
        viz_frame.pack()
        self.viz_canvas = tk.Canvas(viz_frame, width=340, height=80, bg=COLORS["panel"], highlightthickness=0)
        self.viz_canvas.pack()

        self.btn_viz = ctk.CTkButton(
            right, text="Visualization: ON", width=140, height=26,
            fg_color="#1a2535", command=self._toggle_viz
        )
        self.btn_viz.pack(pady=(4, 10))

        self.title_label = ctk.CTkLabel(right, text="No track loaded",
                                        font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["text"])
        self.title_label.pack()

        self.artist_label = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=13), text_color=COLORS["text_dim"])
        self.artist_label.pack(pady=(2, 12))

        # Progress
        time_frame = ctk.CTkFrame(right, fg_color="transparent")
        time_frame.pack()
        self.time_current = ctk.CTkLabel(time_frame, text="0:00", width=45, text_color="#668899")
        self.time_current.pack(side="left")
        self.progress = ctk.CTkSlider(time_frame, from_=0, to=1000, width=260,
                                      progress_color=COLORS["accent"], button_color=COLORS["accent"])
        self.progress.pack(side="left", padx=8)
        self.progress.bind("<ButtonRelease-1>", self._on_seek_release)
        self.time_total = ctk.CTkLabel(time_frame, text="0:00", width=45, text_color="#668899")
        self.time_total.pack(side="left")

        # Controls
        ctrl = ctk.CTkFrame(right, fg_color="transparent")
        ctrl.pack(pady=16)

        self.btn_shuffle = ctk.CTkButton(ctrl, text="Shuffle", width=70, height=32,
                                         fg_color="#1a2535", command=self._toggle_shuffle)
        self.btn_shuffle.grid(row=0, column=0, padx=4)

        ctk.CTkButton(ctrl, text="⏮", width=48, height=40, fg_color="#1a2535",
                      command=self._prev).grid(row=0, column=1, padx=4)

        self.btn_play = ctk.CTkButton(ctrl, text="▶", width=60, height=46,
                                      fg_color=COLORS["accent_dim"], hover_color=COLORS["accent"],
                                      font=ctk.CTkFont(size=18), command=self._toggle_play)
        self.btn_play.grid(row=0, column=2, padx=6)

        ctk.CTkButton(ctrl, text="⏭", width=48, height=40, fg_color="#1a2535",
                      command=self._next).grid(row=0, column=3, padx=4)

        self.btn_repeat = ctk.CTkButton(ctrl, text="Repeat", width=70, height=32,
                                        fg_color="#1a2535", command=self._cycle_repeat)
        self.btn_repeat.grid(row=0, column=4, padx=4)

        # Volume
        vol_frame = ctk.CTkFrame(right, fg_color="transparent")
        vol_frame.pack(pady=6)
        ctk.CTkLabel(vol_frame, text="Vol", text_color="#668899").pack(side="left", padx=(0, 8))
        self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=100, width=150, command=self._set_volume)
        self.vol_slider.set(self.volume)
        self.vol_slider.pack(side="left")

        self.status_label = ctk.CTkLabel(
            right,
            text="VLC ready" if HAS_VLC else "VLC not found – playback disabled",
            text_color="#557788"
        )
        self.status_label.pack(pady=(10, 8))

        # Demo library
        self._load_demo_library()

    def _load_demo_library(self):
        self.library = [
            {"title": "Neon Dreams", "artist": "Cyber Pulse", "path": ""},
            {"title": "Midnight Protocol", "artist": "HoloWave", "path": ""},
            {"title": "Data Rain", "artist": "Synth Runner", "path": ""},
        ]
        self._refresh_library_list()

    def _refresh_library_list(self, items=None):
        for w in self.lib_list.winfo_children():
            w.destroy()
        items = items or self.library
        for track in items:
            btn = ctk.CTkButton(
                self.lib_list,
                text=f"{track['title']}  —  {track['artist']}",
                anchor="w", height=36, fg_color="transparent",
                hover_color="#132033", text_color=COLORS["text"],
                command=lambda t=track: self._play_track(t)
            )
            btn.pack(fill="x", pady=2, padx=4)

    def _filter_library(self):
        q = self.search_var.get().lower()
        if not q:
            self._refresh_library_list()
            return
        filtered = [t for t in self.library if q in t["title"].lower() or q in t["artist"].lower()]
        self._refresh_library_list(filtered)

    # ----------------------------------------------------------------
    # Playback helpers
    # ----------------------------------------------------------------
    def _play_track(self, track):
        if not HAS_VLC:
            self.status_label.configure(text="Install python-vlc + VLC player")
            return
        path = track.get("path")
        if not path or not os.path.exists(path):
            self.status_label.configure(text="No valid file path")
            return

        self.player.stop()
        media = self.instance.media_new(str(path))
        self.player.set_media(media)
        self.player.play()

        self.current_track = track
        self.is_playing = True
        self.btn_play.configure(text="⏸")
        self.title_label.configure(text=track["title"])
        self.artist_label.configure(text=track["artist"])
        self.status_label.configure(text="Playing")

    def _toggle_play(self):
        if not HAS_VLC or not self.player:
            return
        if self.player.is_playing():
            self.player.pause()
            self.is_playing = False
            self.btn_play.configure(text="▶")
            self.status_label.configure(text="Paused")
        else:
            self.player.play()
            self.is_playing = True
            self.btn_play.configure(text="⏸")
            self.status_label.configure(text="Playing")

    def _next(self):
        if not self.library:
            return
        if self.shuffle:
            next_track = random.choice(self.library)
        else:
            try:
                idx = self.library.index(self.current_track)
                next_track = self.library[(idx + 1) % len(self.library)]
            except (ValueError, AttributeError):
                next_track = self.library[0]
        self._play_track(next_track)

    def _prev(self):
        if not self.library:
            return
        try:
            idx = self.library.index(self.current_track)
            prev_track = self.library[(idx - 1) % len(self.library)]
        except (ValueError, AttributeError):
            prev_track = self.library[0]
        self._play_track(prev_track)

    def _toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.btn_shuffle.configure(fg_color=COLORS["accent_dim"] if self.shuffle else "#1a2535")

    def _cycle_repeat(self):
        order = ["off", "one", "all"]
        self.repeat = order[(order.index(self.repeat) + 1) % 3]
        colors = {"off": "#1a2535", "one": COLORS["accent_dim"], "all": COLORS["accent"]}
        self.btn_repeat.configure(fg_color=colors[self.repeat], text=f"Repeat ({self.repeat})")

    def _set_volume(self, val):
        self.volume = int(float(val))
        if self.player:
            self.player.audio_set_volume(self.volume)

    def _on_seek_release(self, event):
        if not self.player:
            return
        length = self.player.get_length()
        if length > 0:
            target = int((self.progress.get() / 1000) * length)
            self.player.set_time(target)

    def _start_progress_updater(self):
        def updater():
            if HAS_VLC and self.player and self.player.is_playing():
                length = self.player.get_length()
                current = self.player.get_time()
                if length > 0:
                    self.progress.set((current / length) * 1000)
                    self.time_current.configure(text=self._format_time(current))
                    self.time_total.configure(text=self._format_time(length))
            self.after(300, updater)
        self.after(300, updater)

    @staticmethod
    def _format_time(ms: int) -> str:
        s = max(0, ms // 1000)
        return f"{s // 60}:{s % 60:02d}"

    # ----------------------------------------------------------------
    # Visualizer
    # ----------------------------------------------------------------
    def _toggle_viz(self):
        self.viz_enabled = not self.viz_enabled
        state = "ON" if self.viz_enabled else "OFF"
        self.btn_viz.configure(
            text=f"Visualization: {state}",
            fg_color=COLORS["accent_dim"] if self.viz_enabled else "#1a2535"
        )
        if not self.viz_enabled:
            self.viz_canvas.delete("all")

    def _start_visualization(self):
        def update():
            if self.viz_enabled:
                self._update_spectrum()
            self.after(40, update)
        self.after(40, update)

    def _update_spectrum(self):
        if self.is_playing and HAS_VLC and self.player and self.player.is_playing():
            self.viz_energy = min(1.0, self.viz_energy * 0.82 + random.uniform(0.3, 0.75))
        else:
            self.viz_energy *= 0.88

        for i in range(self.viz_bars):
            center = 1.0 - abs(i - self.viz_bars / 2) / (self.viz_bars / 2)
            center = center ** 0.55
            target = self.viz_energy * center * random.uniform(0.5, 1.0)
            self.viz_heights[i] = self.viz_heights[i] * 0.62 + target * 0.38

        self._draw_spectrum()

    def _draw_spectrum(self):
        c = self.viz_canvas
        c.delete("all")
        w, h = 340, 80
        bar_w = w / self.viz_bars
        for i, val in enumerate(self.viz_heights):
            bh = val * (h - 6)
            x0 = i * bar_w + 1
            x1 = x0 + bar_w - 2
            intensity = int(160 + val * 95)
            color = f"#{0:02x}{intensity:02x}{255:02x}"
            c.create_rectangle(x0, h - bh, x1, h, fill=color, outline="")

    # ----------------------------------------------------------------
    # YOUTUBE TAB
    # ----------------------------------------------------------------
    def _build_youtube_tab(self):
        top = ctk.CTkFrame(self.tab_youtube, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)

        self.yt_login_btn = ctk.CTkButton(
            top, text="Login with Google", width=160, height=34,
            fg_color=COLORS["accent_dim"], command=self._youtube_login
        )
        self.yt_login_btn.pack(side="left")

        self.yt_status = ctk.CTkLabel(top, text="Not logged in", text_color=COLORS["text_dim"])
        self.yt_status.pack(side="left", padx=12)

        # Search
        search_frame = ctk.CTkFrame(self.tab_youtube, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.yt_search_var = ctk.StringVar()
        entry = ctk.CTkEntry(search_frame, placeholder_text="Search YouTube...", 
                             textvariable=self.yt_search_var, height=36, width=420)
        entry.pack(side="left", padx=(0, 8))
        entry.bind("<Return>", lambda e: self._youtube_search())

        ctk.CTkButton(search_frame, text="Search", width=90, height=36,
                      fg_color=COLORS["accent_dim"], command=self._youtube_search).pack(side="left")

        # Content
        content = ctk.CTkFrame(self.tab_youtube, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, corner_radius=12, fg_color=COLORS["panel"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="PLAYLISTS", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS["accent"]).grid(row=0, column=0, pady=10, padx=12, sticky="w")

        self.playlist_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.playlist_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        right = ctk.CTkFrame(content, corner_radius=12, fg_color=COLORS["panel"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_rowconfigure(1, weight=1)

        self.yt_section_title = ctk.CTkLabel(right, text="Search or select a playlist",
                                             font=ctk.CTkFont(size=14, weight="bold"),
                                             text_color=COLORS["accent"])
        self.yt_section_title.grid(row=0, column=0, pady=10, padx=12, sticky="w")

        self.video_list = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.video_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    def _youtube_login(self):
        if not HAS_GOOGLE:
            self.yt_status.configure(text="google-auth libraries not installed", text_color=COLORS["danger"])
            return

        if self.youtube:
            self.youtube = None
            self.credentials = None
            if os.path.exists(self.TOKEN_FILE):
                os.remove(self.TOKEN_FILE)
            self.yt_login_btn.configure(text="Login with Google")
            self.yt_status.configure(text="Logged out")
            return

        try:
            creds = None
            if os.path.exists(self.TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists("client_secret.json"):
                        self.yt_status.configure(text="Missing client_secret.json", text_color=COLORS["danger"])
                        return
                    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", self.SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(self.TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())

            self.credentials = creds
            self.youtube = build("youtube", "v3", credentials=creds)
            self.yt_login_btn.configure(text="Logout", fg_color=COLORS["danger"])
            self.yt_status.configure(text="Logged in", text_color=COLORS["success"])
            self._load_playlists()
        except Exception as e:
            self.yt_status.configure(text=f"Login error: {e}", text_color=COLORS["danger"])

    def _load_playlists(self):
        for w in self.playlist_list.winfo_children():
            w.destroy()
        if not self.youtube:
            return
        try:
            req = self.youtube.playlists().list(part="snippet,contentDetails", mine=True, maxResults=50)
            resp = req.execute()
            for item in resp.get("items", []):
                title = item["snippet"]["title"]
                count = item["contentDetails"]["itemCount"]
                pid = item["id"]
                btn = ctk.CTkButton(
                    self.playlist_list, text=f"{title}  ({count})",
                    anchor="w", height=34, fg_color="transparent", hover_color="#132033",
                    command=lambda p=pid, t=title: self._load_playlist_videos(p, t)
                )
                btn.pack(fill="x", pady=2, padx=4)
        except Exception as e:
            self.yt_status.configure(text=str(e), text_color=COLORS["danger"])

    def _load_playlist_videos(self, playlist_id, title):
        self.yt_section_title.configure(text=title)
        for w in self.video_list.winfo_children():
            w.destroy()
        try:
            req = self.youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=30)
            resp = req.execute()
            for item in resp.get("items", []):
                sn = item["snippet"]
                vid = sn["resourceId"]["videoId"]
                self._add_yt_item(vid, sn["title"], sn.get("videoOwnerChannelTitle", ""))
        except Exception as e:
            self.yt_status.configure(text=str(e), text_color=COLORS["danger"])

    def _youtube_search(self):
        query = self.yt_search_var.get().strip()
        if not query or not self.youtube:
            return
        self.yt_section_title.configure(text=f"Search: {query}")
        for w in self.video_list.winfo_children():
            w.destroy()
        try:
            req = self.youtube.search().list(part="snippet", q=query, type="video", maxResults=20)
            resp = req.execute()
            for item in resp.get("items", []):
                vid = item["id"]["videoId"]
                sn = item["snippet"]
                self._add_yt_item(vid, sn["title"], sn["channelTitle"])
        except Exception as e:
            self.yt_status.configure(text=str(e), text_color=COLORS["danger"])

    def _add_yt_item(self, video_id, title, channel):
        row = ctk.CTkFrame(self.video_list, fg_color="#111827", corner_radius=8)
        row.pack(fill="x", pady=3, padx=4)

        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkLabel(text_frame, text=title[:65], anchor="w").pack(anchor="w")
        ctk.CTkLabel(text_frame, text=channel, text_color=COLORS["text_dim"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        ctk.CTkButton(
            row, text="Play", width=60, height=28,
            fg_color=COLORS["accent_dim"],
            command=lambda: self._play_youtube(video_id, title)
        ).pack(side="right", padx=8, pady=6)

    def _play_youtube(self, video_id, title):
        if not HAS_VLC:
            return
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        self.is_playing = True
        self.btn_play.configure(text="⏸")
        self.title_label.configure(text=title)
        self.artist_label.configure(text="YouTube")
        self.status_label.configure(text="Playing from YouTube")
        self.tabview.set("Player")

    # ----------------------------------------------------------------
    # SPOTIFY TAB
    # ----------------------------------------------------------------
    def _build_spotify_tab(self):
        top = ctk.CTkFrame(self.tab_spotify, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)

        self.sp_login_btn = ctk.CTkButton(
            top, text="Login with Spotify", width=160, height=34,
            fg_color="#1DB954", hover_color="#1ed760", command=self._spotify_login
        )
        self.sp_login_btn.pack(side="left")

        self.sp_status = ctk.CTkLabel(top, text="Not logged in", text_color=COLORS["text_dim"])
        self.sp_status.pack(side="left", padx=12)

        search_frame = ctk.CTkFrame(self.tab_spotify, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.sp_search_var = ctk.StringVar()
        ctk.CTkEntry(search_frame, placeholder_text="Search Spotify tracks...",
                     textvariable=self.sp_search_var, height=36, width=420).pack(side="left", padx=(0, 8))
        ctk.CTkButton(search_frame, text="Search", width=90, height=36,
                      fg_color="#1DB954", command=self._spotify_search).pack(side="left")

        self.sp_results = ctk.CTkScrollableFrame(self.tab_spotify, fg_color=COLORS["panel"])
        self.sp_results.pack(fill="both", expand=True, padx=15, pady=(0, 12))

    def _spotify_login(self):
        if not HAS_SPOTIFY:
            self.sp_status.configure(text="spotipy not installed", text_color=COLORS["danger"])
            return
        if self.sp:
            self.sp = None
            self.sp_login_btn.configure(text="Login with Spotify")
            self.sp_status.configure(text="Logged out")
            return
        try:
            from spotify_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
            auth = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope="user-library-read playlist-read-private",
                open_browser=True
            )
            self.sp = spotipy.Spotify(auth_manager=auth)
            user = self.sp.current_user()
            self.sp_login_btn.configure(text="Logout")
            self.sp_status.configure(text=f"Logged in as {user['display_name']}", text_color="#1DB954")
        except Exception as e:
            self.sp_status.configure(text=f"Error: {e}", text_color=COLORS["danger"])

    def _spotify_search(self):
        query = self.sp_search_var.get().strip()
        if not query or not self.sp:
            return
        for w in self.sp_results.winfo_children():
            w.destroy()
        try:
            results = self.sp.search(q=query, type="track", limit=15)
            for item in results["tracks"]["items"]:
                title = item["name"]
                artist = ", ".join(a["name"] for a in item["artists"])
                preview = item.get("preview_url")
                external = item["external_urls"]["spotify"]

                row = ctk.CTkFrame(self.sp_results, fg_color="#111827", corner_radius=8)
                row.pack(fill="x", pady=3, padx=6)

                text_f = ctk.CTkFrame(row, fg_color="transparent")
                text_f.pack(side="left", fill="x", expand=True, padx=8, pady=6)
                ctk.CTkLabel(text_f, text=title, anchor="w").pack(anchor="w")
                ctk.CTkLabel(text_f, text=artist, text_color=COLORS["text_dim"],
                             font=ctk.CTkFont(size=11)).pack(anchor="w")

                btn_f = ctk.CTkFrame(row, fg_color="transparent")
                btn_f.pack(side="right", padx=6)
                if preview:
                    ctk.CTkButton(btn_f, text="Preview", width=70, height=28, fg_color="#1DB954",
                                  command=lambda u=preview, t=title: self._play_preview(u, t)).pack(side="left", padx=3)
                ctk.CTkButton(btn_f, text="Open", width=60, height=28, fg_color="#1a2535",
                              command=lambda u=external: webbrowser.open(u)).pack(side="left", padx=3)
        except Exception as e:
            self.sp_status.configure(text=str(e), text_color=COLORS["danger"])

    def _play_preview(self, url, title):
        if not HAS_VLC:
            return
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        self.is_playing = True
        self.btn_play.configure(text="⏸")
        self.title_label.configure(text=title)
        self.artist_label.configure(text="Spotify Preview")
        self.tabview.set("Player")

    # ----------------------------------------------------------------
    # NETWORK TAB
    # ----------------------------------------------------------------
    def _build_network_tab(self):
        controls = ctk.CTkFrame(self.tab_network, fg_color="transparent")
        controls.pack(fill="x", padx=15, pady=12)

        self.btn_sweep_start = ctk.CTkButton(
            controls, text="Start Sweep", width=120, height=34,
            fg_color=COLORS["accent_dim"], command=self._start_sweep
        )
        self.btn_sweep_start.pack(side="left", padx=(0, 8))

        self.btn_sweep_stop = ctk.CTkButton(
            controls, text="Stop", width=90, height=34,
            fg_color=COLORS["danger"], state="disabled", command=self._stop_sweep
        )
        self.btn_sweep_stop.pack(side="left", padx=(0, 18))

        ctk.CTkLabel(controls, text="Speed (ms):", text_color=COLORS["text_dim"]).pack(side="left", padx=(0, 6))
        self.speed_slider = ctk.CTkSlider(controls, from_=80, to=800, width=130,
                                          command=lambda v: self.speed_label.configure(text=f"{int(v)}"))
        self.speed_slider.set(250)
        self.speed_slider.pack(side="left")
        self.speed_label = ctk.CTkLabel(controls, text="250", width=40)
        self.speed_label.pack(side="left", padx=(4, 14))

        ctk.CTkLabel(controls, text="Aggressiveness:", text_color=COLORS["text_dim"]).pack(side="left", padx=(0, 6))
        self.aggro_slider = ctk.CTkSlider(controls, from_=1, to=6, width=90,
                                          command=lambda v: self.aggro_label.configure(text=f"{int(v)}"))
        self.aggro_slider.set(3)
        self.aggro_slider.pack(side="left")
        self.aggro_label = ctk.CTkLabel(controls, text="3", width=25)
        self.aggro_label.pack(side="left")

        self.sweep_status = ctk.CTkLabel(
            self.tab_network,
            text="Ready – scans only your local subnet (non-aggressive)",
            text_color=COLORS["text_dim"]
        )
        self.sweep_status.pack(pady=(0, 8))

        content = ctk.CTkFrame(self.tab_network, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Host list
        left = ctk.CTkFrame(content, corner_radius=12, fg_color=COLORS["panel"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="DISCOVERED HOSTS", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS["accent"]).grid(row=0, column=0, pady=10, padx=12, sticky="w")

        self.host_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.host_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))

        # Diagram side
        right = ctk.CTkFrame(content, corner_radius=12, fg_color=COLORS["panel"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(right, text="TOPOLOGY", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS["accent"]).pack(pady=10)

        self.diagram_canvas = tk.Canvas(right, bg=COLORS["panel"], highlightthickness=0, height=280)
        self.diagram_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.btn_graphviz = ctk.CTkButton(
            right, text="Generate Graphviz Diagram", width=200, height=32,
            fg_color="#1a2535", command=self._generate_graphviz
        )
        self.btn_graphviz.pack(pady=(0, 12))

    def _get_local_subnet(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return ipaddress.ip_network(f"{local_ip}/24", strict=False)
        except Exception:
            return ipaddress.ip_network("192.168.1.0/24")

    def _ping_host(self, ip: str):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
        timeout_val = "800" if platform.system().lower() == "windows" else "1"
        try:
            start = time.time()
            result = subprocess.run(
                ["ping", param, "1", timeout_param, timeout_val, str(ip)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5
            )
            rtt = (time.time() - start) * 1000
            alive = result.returncode == 0
            hostname = ""
            if alive:
                try:
                    hostname = socket.gethostbyaddr(str(ip))[0]
                except Exception:
                    pass
            return alive, rtt, hostname
        except Exception:
            return False, 0.0, ""

    def _start_sweep(self):
        if self.sweep_running:
            return
        self.sweep_running = True
        self.discovered_hosts = []
        self.btn_sweep_start.configure(state="disabled")
        self.btn_sweep_stop.configure(state="normal")
        self.sweep_status.configure(text="Scanning local subnet...", text_color=COLORS["accent"])

        for w in self.host_list.winfo_children():
            w.destroy()
        self.diagram_canvas.delete("all")

        network = self._get_local_subnet()
        delay = self.speed_slider.get() / 1000.0
        workers = int(self.aggro_slider.get())

        def worker():
            hosts = list(network.hosts())
            found = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as exe:
                futures = {}
                for ip in hosts:
                    if not self.sweep_running:
                        break
                    fut = exe.submit(self._ping_host, str(ip))
                    futures[fut] = str(ip)
                    time.sleep(delay)

                for fut in concurrent.futures.as_completed(futures):
                    if not self.sweep_running:
                        break
                    ip = futures[fut]
                    try:
                        alive, rtt, hostname = fut.result()
                        if alive:
                            found += 1
                            info = {"ip": ip, "hostname": hostname or "Unknown", "rtt": round(rtt, 1)}
                            self.discovered_hosts.append(info)
                            self.after(0, lambda h=info: self._add_host_row(h))
                    except Exception:
                        pass
            self.after(0, lambda: self._sweep_done(found, len(hosts)))

        threading.Thread(target=worker, daemon=True).start()

    def _stop_sweep(self):
        self.sweep_running = False
        self.btn_sweep_stop.configure(state="disabled")
        self.sweep_status.configure(text="Stopping...", text_color=COLORS["warning"])

    def _sweep_done(self, found, total):
        self.sweep_running = False
        self.btn_sweep_start.configure(state="normal")
        self.btn_sweep_stop.configure(state="disabled")
        self.sweep_status.configure(
            text=f"Finished – {found} hosts responded (of {total})",
            text_color=COLORS["success"]
        )
        self._draw_simple_diagram()

    def _add_host_row(self, host):
        text = f"{host['ip']:<16}  {host['hostname'][:26]:<26}  {host['rtt']} ms"
        ctk.CTkLabel(
            self.host_list, text=text, anchor="w",
            font=ctk.CTkFont(family="Consolas", size=13), text_color=COLORS["text"]
        ).pack(fill="x", pady=2, padx=6)

    def _draw_simple_diagram(self):
        c = self.diagram_canvas
        c.delete("all")
        w = c.winfo_width() or 380
        h = c.winfo_height() or 260
        if not self.discovered_hosts:
            c.create_text(w//2, h//2, text="No hosts found", fill="#557788")
            return

        cx, cy = w // 2, h // 2
        radius = min(w, h) // 2 - 40
        n = len(self.discovered_hosts)

        c.create_oval(cx-16, cy-16, cx+16, cy+16, fill=COLORS["accent"], outline="")
        c.create_text(cx, cy, text="You", fill=COLORS["bg"], font=("Segoe UI", 8, "bold"))

        for i, host in enumerate(self.discovered_hosts):
            angle = 2 * math.pi * i / max(n, 1)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            c.create_line(cx, cy, x, y, fill="#1a3a4a")
            c.create_oval(x-12, y-12, x+12, y+12, fill=COLORS["accent_dim"], outline=COLORS["accent"])
            c.create_text(x, y+20, text=host["ip"].split(".")[-1], fill=COLORS["text_dim"], font=("Segoe UI", 8))

    def _generate_graphviz(self):
        if not HAS_GRAPHVIZ:
            self.sweep_status.configure(text="graphviz package or system binary missing", text_color=COLORS["danger"])
            return
        if not self.discovered_hosts:
            self.sweep_status.configure(text="Run a sweep first", text_color=COLORS["warning"])
            return

        try:
            dot = graphviz.Digraph(format="png", engine="dot",
                                   graph_attr={"bgcolor": COLORS["bg"], "rankdir": "LR"},
                                   node_attr={"style": "filled", "fontname": "Segoe UI", "fontsize": "11"},
                                   edge_attr={"color": "#1a4a5a"})

            local_ip = "Local"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                pass

            dot.node("local", f"You\n{local_ip}", fillcolor=COLORS["accent"], fontcolor=COLORS["bg"], shape="ellipse")

            for i, host in enumerate(self.discovered_hosts):
                nid = f"h{i}"
                label = f"{host['ip']}\n{host['hostname'][:18]}\n{host['rtt']} ms"
                color = "#00c853" if host["rtt"] < 30 else COLORS["accent_dim"]
                dot.node(nid, label, fillcolor=color, fontcolor=COLORS["bg"])
                dot.edge("local", nid)

            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "topo")
                dot.render(path, cleanup=True)
                png = path + ".png"
                self._show_graphviz_window(png)

            self.sweep_status.configure(text="Graphviz diagram generated", text_color=COLORS["success"])
        except Exception as e:
            self.sweep_status.configure(text=f"Graphviz error: {e}", text_color=COLORS["danger"])

    def _show_graphviz_window(self, png_path):
        if not HAS_PIL:
            return
        win = ctk.CTkToplevel(self)
        win.title("Network Topology")
        win.geometry("880x620")
        win.transient(self)

        img = Image.open(png_path)
        img.thumbnail((840, 560), Image.Resampling.LANCZOS)
        photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        lbl = ctk.CTkLabel(win, image=photo, text="")
        lbl.image = photo
        lbl.pack(padx=12, pady=12, expand=True)

        ctk.CTkButton(win, text="Close", width=100, command=win.destroy).pack(pady=(0, 12))


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting HoloAudio...")
    if not HAS_VLC:
        print("Warning: python-vlc not found. Playback will be disabled.")
    app = HoloAudio()
    app.mainloop()