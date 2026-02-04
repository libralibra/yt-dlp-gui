import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import re
import os
import sys
import signal


class YtDlpGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("yt-dlp GUI")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        self.style = ttk.Style()
        self.style.configure("TButton", padding=5)
        self.style.configure("TLabel", padding=5)

        self.process = None
        self.is_downloading = False
        self.stop_requested = False
        self.current_filename = None

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # 1. yt-dlp path
        row = 0
        ttk.Label(main_frame, text="yt-dlp Path:").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.ytdlp_path = ttk.Entry(main_frame)
        self.ytdlp_path.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        self.auto_detect_ytdlp()
        ttk.Button(main_frame, text="Browse...", command=self.browse_ytdlp).grid(
            row=row, column=2, padx=5
        )

        # 2. download path
        row += 1
        ttk.Label(main_frame, text="Download Path:").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.save_path = ttk.Entry(main_frame)
        self.save_path.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5)
        default_download = os.path.join(
            os.environ.get("USERPROFILE", os.environ.get("HOME", "")), "Downloads"
        )
        self.save_path.insert(0, default_download)
        ttk.Button(main_frame, text="Browse...", command=self.browse_save_path).grid(
            row=row, column=2, padx=5
        )

        # 3. download type
        row += 1
        ttk.Label(main_frame, text="Download Type:").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.download_type = ttk.Combobox(
            main_frame, values=["Video", "Audio"], state="readonly"
        )
        self.download_type.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.download_type.set("Video")
        self.download_type.bind("<<ComboboxSelected>>", self.on_download_type_change)

        # 4. quality/format
        row += 1
        ttk.Label(main_frame, text="Quality/Format:").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        # 2 dropdown lists side by side
        quality_frame = ttk.Frame(main_frame)
        quality_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        quality_frame.columnconfigure(0, weight=3)  # quality
        quality_frame.columnconfigure(1, weight=1)  # format
        quality_frame.columnconfigure(2, weight=0)  # fixed label

        # quality dropdown
        self.quality_combo = ttk.Combobox(quality_frame, state="readonly")
        self.quality_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        # format dropdown
        self.format_combo = ttk.Combobox(quality_frame, width=10, state="readonly")
        self.format_combo.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(quality_frame, text="(Quality | Format)").grid(
            row=0, column=2, sticky=tk.W, padx=(5, 0)
        )

        # initialise options
        self.update_quality_options()
        self.update_format_options()

        # URL
        row += 1
        ttk.Label(main_frame, text="Video URL:").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.url_entry = ttk.Entry(main_frame)
        self.url_entry.grid(
            row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5
        )
        self.url_entry.insert(0, "https://www.youtube.com/watch?v=...")
        self.url_entry.bind("<FocusOut>", self.check_url_type)
        self.url_entry.bind("<KeyRelease>", self.check_url_type)

        self.url_type_label = ttk.Label(main_frame, text="", foreground="blue")
        self.url_type_label.grid(
            row=row + 1, column=1, columnspan=2, sticky=tk.W, padx=5
        )

        # 5. download button
        row += 2
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)
        self.download_btn = ttk.Button(
            button_frame,
            text="▶ Start download",
            command=self.start_download,
            width=20,
        )
        self.download_btn.pack()

        # progress bar
        row += 1
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            length=400,
        )
        self.progress_bar.grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5
        )
        self.progress_label = ttk.Label(main_frame, text="Ready", foreground="gray")
        self.progress_label.grid(row=row + 1, column=0, columnspan=3, pady=2)

        # log detail
        row += 2
        ttk.Label(main_frame, text="Download Log:").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.log_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            height=20,
            font=("Consolas", 10),
            bg="#f5f5f5",
            fg="#333333",
        )
        self.log_text.grid(
            row=row + 1,
            column=0,
            columnspan=3,
            sticky=(tk.W, tk.E, tk.N, tk.S),
            padx=5,
            pady=5,
        )
        main_frame.rowconfigure(row + 1, weight=1)
        ttk.Button(main_frame, text="Clear Log", command=self.clear_log).grid(
            row=row, column=2, sticky=tk.E, pady=5
        )

    def check_url_type(self, event=None):
        url = self.url_entry.get().strip()
        if not url or "..." in url:
            self.url_type_label.config(text="")
            return
        if self.is_playlist_url(url):
            self.url_type_label.config(
                text="⚠️ Detected playlist, will only download current video",
                foreground="orange",
            )
        else:
            self.url_type_label.config(text="✓ Single video link", foreground="green")

    def is_playlist_url(self, url):
        if "list=" in url and "youtube.com" in url:
            return True
        if "music.youtube.com" in url and "list=" in url:
            return True
        if "bilibili.com" in url and "plist=" in url:
            return True
        playlist_indicators = ["playlist", "list=", "album=", "page="]
        return any(indicator in url.lower() for indicator in playlist_indicators)

    def auto_detect_ytdlp(self):
        possible_paths = [
            "yt-dlp.exe",
            "yt-dlp",
            os.path.expanduser("~/yt-dlp.exe"),
            os.path.expanduser("~/yt-dlp"),
            "/usr/local/bin/yt-dlp",
            "/usr/bin/yt-dlp",
            "C:/yt-dlp/yt-dlp.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path) or self.command_exists(path):
                self.ytdlp_path.insert(0, path)
                return
        self.ytdlp_path.insert(0, "yt-dlp.exe")

    def command_exists(self, cmd):
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            return True
        except:
            return False

    def browse_ytdlp(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = filedialog.askopenfilename(
            title="Choose yt-dlp executable",
            initialdir=script_dir,
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")],
        )
        if filename:
            self.ytdlp_path.delete(0, tk.END)
            self.ytdlp_path.insert(0, filename)

    def browse_save_path(self):
        directory = filedialog.askdirectory(title="Choose download path")
        if directory:
            self.save_path.delete(0, tk.END)
            self.save_path.insert(0, directory)

    def on_download_type_change(self, event=None):
        """update quality and format options when download type changes"""
        self.update_quality_options()
        self.update_format_options()

    def update_quality_options(self):
        """update quality dropdown based on download type"""
        download_type = self.download_type.get()

        if download_type == "Video":
            qualities = [
                "Auto (Best Quality)",
                "Best Quality (best)",
                "1080p",
                "720p",
                "480p",
                "360p",
                "Only Video (No Audio)",
                "Only Audio Extraction",
            ]
        else:  # Audio
            qualities = [
                "Auto (Best Quality)",
                "Best Quality (320k)",
                "High Quality (256k)",
                "Standard Quality (192k)",
                "Medium Quality (128k)",
                "Low Quality (96k)",
            ]

        self.quality_combo["values"] = qualities
        self.quality_combo.set(qualities[0])

    def update_format_options(self):
        """update format dropdown based on download type"""
        download_type = self.download_type.get()

        if download_type == "Video":
            # video format, default mp4
            formats = ["mp4", "webm", "mkv", "mov", "avi"]
            self.format_combo["values"] = formats
            self.format_combo.set("mp4")
        else:
            # audio format, default mp3
            formats = ["mp3", "m4a", "wav", "flac", "opus"]
            self.format_combo["values"] = formats
            self.format_combo.set("mp3")

    def get_quality_option(self):
        """get quality parameter for yt-dlp based on selection"""
        download_type = self.download_type.get()
        quality = self.quality_combo.get()

        if download_type == "Video":
            quality_map = {
                "Auto (Best Quality)": "",
                "Best Quality (best)": "-f best",
                "1080p": '-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]"',
                "720p": '-f "bestvideo[height<=720]+bestaudio/best[height<=720]"',
                "480p": '-f "bestvideo[height<=480]+bestaudio/best[height<=480]"',
                "360p": '-f "bestvideo[height<=360]+bestaudio/best[height<=360]"',
                "Only Video (No Audio)": "-f bestvideo",
                "Only Audio Extraction": "-f bestaudio",
            }
        else:
            quality_map = {
                "Auto (Best Quality)": "--audio-quality 0",
                "Best Quality (320k)": "--audio-quality 0",
                "High Quality (256k)": "--audio-quality 2",
                "Standard Quality (192k)": "--audio-quality 3",
                "Medium Quality (128k)": "--audio-quality 5",
                "Low Quality (96k)": "--audio-quality 7",
            }

        return quality_map.get(quality, "")

    def get_format_option(self):
        """get output format parameter"""
        download_type = self.download_type.get()
        output_format = self.format_combo.get()

        if download_type == "Video":
            # video: use --remux-video or --merge-output-format to ensure output format
            if output_format:
                return f"--merge-output-format {output_format}"
            return ""
        else:
            # Audio: use --audio-format
            if output_format:
                return f"--extract-audio --audio-format {output_format}"
            return "--extract-audio"

    def log(self, message):
        self.root.after(0, lambda: self._append_log(message))

    def _append_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def update_progress(self, percent, status_text=""):
        self.root.after(0, lambda: self._set_progress(percent, status_text))

    def _set_progress(self, percent, status_text):
        self.progress_var.set(percent)
        if status_text:
            self.progress_label.config(text=status_text, foreground="#2196F3")
        if percent >= 100:
            self.progress_label.config(text="Download Complete!", foreground="green")

    def parse_progress(self, line):
        patterns = [
            r"\[download\]\s+(\d+\.?\d*)%",
            r"(\d+\.?\d*)%",
            r"\[download\].*?(\d+)%",
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        if "[download] 100%" in line:
            return 100
        return None

    def extract_filename(self, line):
        """Extract filename from yt-dlp output line"""
        match = re.search(r"\[download\]\s+Destination:\s+(.+)", line)
        if match:
            return match.group(1).strip()
        match = re.search(r"\[ExtractAudio\]\s+Destination:\s+(.+)", line)
        if match:
            return match.group(1).strip()
        match = re.search(r"\[Fixup\w*\]\s+(.+)", line)
        if match:
            return match.group(1).strip()
        match = re.search(r"Already downloaded:\s+(.+)", line)
        if match:
            return match.group(1).strip()
        return None

    def start_download(self):
        if self.is_downloading:
            messagebox.showwarning("Alert", "Download is already in progress!")
            return

        ytdlp = self.ytdlp_path.get().strip()
        save_dir = self.save_path.get().strip()
        url = self.url_entry.get().strip()

        if not ytdlp:
            messagebox.showerror("Error", "Please specify the yt-dlp path!")
            return
        if not save_dir:
            messagebox.showerror("Error", "Please specify the save path!")
            return
        if not url or "..." in url or not url.startswith("http"):
            messagebox.showerror("Error", "Please enter a valid video URL!")
            return

        os.makedirs(save_dir, exist_ok=True)
        self.stop_requested = False
        self.current_filename = None

        # command line string
        cmd = [ytdlp]

        # add quality option
        quality_opt = self.get_quality_option()
        if quality_opt:
            if '"' in quality_opt:
                parts = quality_opt.split('"')
                for i, part in enumerate(parts):
                    if i % 2 == 0:
                        if part.strip():
                            cmd.extend(part.strip().split())
                    else:
                        cmd.append(part)
            else:
                cmd.extend(quality_opt.split())

        # add format option
        format_opt = self.get_format_option()
        if format_opt:
            cmd.extend(format_opt.split())

        # playlist handling
        if self.is_playlist_url(url):
            cmd.extend(["--no-playlist"])

        # output template (use Video ID to make sure the filename is valid)
        cmd.extend(["-o", os.path.join(save_dir, "%(title)s [%(id)s].%(ext)s")])

        # other options
        cmd.extend(["--newline", "--progress"])

        # add remux option for video format conversion
        if self.download_type.get() == "Video" and self.format_combo.get():
            # make sure ffmpeg can handle format conversion
            pass  # --merge-output-format has been added above

        cmd.append(url)

        self.log_text.delete(1.0, tk.END)
        self.log("=" * 60)
        self.log("Start download...")
        self.log(f"Quality: {self.quality_combo.get()}")
        self.log(f"Format: {self.format_combo.get()}")
        self.log(f"Command: {' '.join(cmd)}")
        self.log("=" * 60)

        self.progress_var.set(0)
        self.progress_label.config(text="Connecting...", foreground="orange")
        self.is_downloading = True
        self.download_btn.config(text="⏹ Stop Download", command=self.stop_download)

        thread = threading.Thread(target=self.run_download, args=(cmd,))
        thread.daemon = True
        thread.start()

    def run_download(self, cmd):
        try:
            if sys.platform == "win32":
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    preexec_fn=os.setsid,
                )

            for line in self.process.stdout:
                if self.stop_requested:
                    break
                line = line.strip()
                if line:
                    self.log(line)
                    filename = self.extract_filename(line)
                    if filename:
                        self.current_filename = filename
                    progress = self.parse_progress(line)
                    if progress is not None:
                        self.update_progress(
                            progress, f"Download progress: {progress:.1f}%"
                        )

            if self.stop_requested:
                self._force_kill_process()
                self.update_progress(0, "Download forcibly stopped")
                self.log("=" * 60)
                self.log("✗ Download forcibly stopped by user")
                return

            return_code = self.process.wait()

            self.log("=" * 60)
            if return_code == 0:
                self.update_progress(100, "Download completed!")
                if self.current_filename and os.path.exists(self.current_filename):
                    self.log(f"✓ Download completed successfully!")
                    self.log(f"File saved at: {self.current_filename}")
                else:
                    save_dir = self.save_path.get().strip()
                    self.log(f"✓ Download completed successfully!")
                    self.log(f"File saved to directory: {save_dir}")
                    try:
                        files = [
                            f
                            for f in os.listdir(save_dir)
                            if os.path.isfile(os.path.join(save_dir, f))
                        ]
                        if files:
                            files.sort(
                                key=lambda x: os.path.getmtime(
                                    os.path.join(save_dir, x)
                                ),
                                reverse=True,
                            )
                            self.log(f"Latest file might be: {files[0]}")
                    except:
                        pass
            else:
                self.update_progress(0, f"Download failed (Error code: {return_code})")
                self.log(f"✗ Download failed, error code: {return_code}")

        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.update_progress(0, f"Error: {str(e)}")
        finally:
            self.is_downloading = False
            self.process = None
            self.stop_requested = False
            self.current_filename = None
            self.root.after(0, self.reset_ui)

    def _force_kill_process(self):
        if self.process is None:
            return
        try:
            if sys.platform == "win32":
                try:
                    os.kill(self.process.pid, signal.CTRL_BREAK_EVENT)
                    self.process.wait(timeout=2)
                except:
                    pass
                if self.process.poll() is None:
                    self.process.kill()
                    self.process.wait()
            else:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    self.process.wait(timeout=2)
                except:
                    pass
                if self.process.poll() is None:
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    except:
                        self.process.kill()
        except Exception as e:
            self.log(f"Error stopping process: {e}")

    def reset_ui(self):
        self.download_btn.config(text="▶ Start Download", command=self.start_download)
        if (
            not self.is_downloading
            and self.progress_var.get() < 100
            and self.progress_var.get() > 0
        ):
            self.progress_label.config(text="Stopped", foreground="red")

    def stop_download(self):
        if not self.is_downloading:
            return
        self.log("=" * 60)
        self.log("User requested to stop download, forcibly terminating process...")
        self.stop_requested = True
        self._force_kill_process()
        self.is_downloading = False
        self.update_progress(0, "Stopped")
        self.reset_ui()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.progress_label.config(text="Ready", foreground="gray")


def main():
    root = tk.Tk()
    app = YtDlpGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
