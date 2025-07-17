import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import threading
import sys


class FFmpegConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Video Converter")
        self.root.geometry("1000x650")

        # Input files
        self.file_paths = []
        self.output_dir = ""

        # Output format
        self.output_format_options = [
            ".mp4 h264",
            ".mp4 h264 (cuda accelerated encoding)",
            ".mp4 h265",
            ".mp4 h265 (cuda accelerated encoding)",
            ".avi"
        ]
        self.output_format_var = tk.StringVar(value=self.output_format_options[3])  # default

        # Widgets

        self.files_label = tk.Label(root, text="Файлы не выбраны", justify="left")
        self.files_label.pack(pady=5)

        self.select_button = tk.Button(root, text="Выбрать файлы", command=self.select_files)
        self.select_button.pack(pady=5)

        # Audio stream input
        self.audio_stream_label = tk.Label(root, text="Номер аудиодорожки\n(оставьте пустым, чтобы использовать стандартную):")
        self.audio_stream_label.pack(pady=5)

        self.audio_stream_entry = tk.Entry(root)
        self.audio_stream_entry.insert(0, "")  # Default: no audio
        self.audio_stream_entry.pack(pady=5)

        # Output folder warning
        self.output_dir_warning = tk.Label(root, text="Выходная папка не выбрана!", fg="red")
        self.output_dir_warning.pack(pady=2)
        self.output_dir_warning_visible = True

        self.output_button = tk.Button(root, text="Выбрать выходную папку", command=self.select_output_dir)
        self.output_button.pack(pady=5)

        self.format_label = tk.Label(root, text="Выходной формат:")
        self.format_label.pack(pady=5)

        self.format_menu = tk.OptionMenu(root, self.output_format_var, *self.output_format_options)
        self.format_menu.pack(pady=5)

        self.bitrate_label = tk.Label(root, text="Битрейт (например: 620k, 2M):")
        self.bitrate_label.pack(pady=5)

        self.bitrate_entry = tk.Entry(root)
        self.bitrate_entry.insert(0, "620k")
        self.bitrate_entry.pack(pady=5)

        self.convert_button = tk.Button(root, text="Начать конвертацию", command=self.start_conversion)
        self.convert_button.pack(pady=10)

        # Button to show audio tracks
        self.show_audio_button = tk.Button(
            root,
            text="Показать аудиодорожки",
            command=self.show_audio_tracks
        )
        self.show_audio_button.pack(pady=5)

        # Console output
        self.console = tk.Text(root, height=10, wrap='word', state='disabled', bg='black', fg='white')
        self.console.pack(padx=10, pady=10, fill='both', expand=True)

        # Scrollbar for console
        scrollbar = tk.Scrollbar(self.console, command=self.console.yview)
        scrollbar.pack(side='right', fill='y')
        self.console.config(yscrollcommand=scrollbar.set)

        # Status bar
        self.status_label = tk.Label(root, text="Выберите файлы", fg="green")
        self.status_label.pack(pady=5)

    def select_files(self):
        filetypes = (("Video files", "*.mp4 *.avi *.mkv *.mov *.flv"), ("All files", "*.*"))
        files = filedialog.askopenfilenames(title="Выберите видеофайлы", filetypes=filetypes)
        if files:
            self.file_paths = list(files)
            self.files_label.config(text="\n".join(self.file_paths))
            self.status_label.config(text="Файлы выбраны.")

    def show_audio_tracks(self):
        filetypes = (("Video files", "*.mp4 *.avi *.mkv *.mov *.flv"), ("All files", "*.*"))
        filepath = filedialog.askopenfilename(title="Выберите файл для просмотра аудиодорожек", filetypes=filetypes)
        if not filepath:
            return

        # Run ffprobe to get audio streams
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            filepath
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'  # or 'ignore'
                )
            
            info = result.stdout
            data = eval(info)  # Safely parse JSON later if needed

            streams = data.get('streams', [])
            audio_streams = [s for s in streams if s.get('codec_type') == 'audio']

            if not audio_streams:
                messagebox.showinfo("Аудиодорожки", "В выбранном файле нет аудиодорожек.")
                return

            msg = "Доступные аудиодорожки:\n"
            for idx, stream in enumerate(audio_streams):
                codec = stream.get('codec_name', 'unknown')
                lang = stream.get('tags', {}).get('language', 'und')
                title = stream.get('tags', {}).get('title', f'Аудиодорожка {idx}')
                msg += f"Дорожка {idx}: {title} ({lang}), кодек: {codec}\n"

            # Show in message box
            messagebox.showinfo("Аудиодорожки", msg)
            self.log(msg + "\n")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить информацию об аудио:\n{e}")

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="Выберите выходную папку")
        if directory:
            self.output_dir = directory
            self.output_dir_warning.config(text="Выходная папка: " + self.output_dir, fg="green")

    def get_ffmpeg_params(self, selected_format, bitrate):
        params = {}

        if selected_format.startswith(".mp4"):
            if "h264" in selected_format:
                params["video_codec"] = "h264_nvenc" if "cuda" in selected_format else "libx264"
                params["ext"] = ".mp4"
            elif "h265" in selected_format:
                params["video_codec"] = "hevc_nvenc" if "cuda" in selected_format else "libx265"
                params["ext"] = ".mp4"
        elif selected_format == ".avi":
            params["video_codec"] = "libxvid"
            params["ext"] = ".avi"

        params["bitrate"] = bitrate
        return params

    def convert_file(self, input_path, output_path, ffmpeg_params, audio_stream_index):
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', ffmpeg_params["video_codec"],
                '-b:v', ffmpeg_params["bitrate"],
            ]

            # Add audio processing if stream index is provided
            if audio_stream_index.strip():
                cmd += [
                    '-map', f'0:a:{audio_stream_index}'  # Map selected audio stream
                ]

            cmd += [output_path]

            self.log(f"Running command: {' '.join(cmd)}\n")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if process.stdout:
                for line in process.stdout:
                    self.log(line)

            process.wait()
            if process.returncode != 0:
                self.log(f"Error during conversion of {input_path}\n", "red")

        except Exception as e:
            self.log(f"Exception: {e}\n")
            messagebox.showerror("Ошибка", f"Ошибка при конвертации файла:\n{input_path}\n{e}")

    def log(self, message, color="white"):
        def append():
            self.console.config(state='normal')
            # Define tags if not already defined
            if not hasattr(self, '_log_tags_initialized'):
                self.console.tag_configure("green", foreground="green")
                self.console.tag_configure("red", foreground="red")
                self.console.tag_configure("white", foreground="white")
                self._log_tags_initialized = True
            # Insert message with the specified color tag
            self.console.insert(tk.END, message, (color,))
            self.console.config(state='disabled')
            self.console.see(tk.END)
        self.root.after(0, append)

    def conversion_thread(self):
        bitrate = self.bitrate_entry.get().strip()
        selected_format = self.output_format_var.get()
        audio_stream_index = self.audio_stream_entry.get().strip()  # Get audio stream index

        if not bitrate:
            messagebox.showwarning("Внимание", "Введите битрейт.")
            return

        if not self.file_paths:
            messagebox.showwarning("Внимание", "Сначала выберите файлы.")
            return

        ffmpeg_params = self.get_ffmpeg_params(selected_format, bitrate)

        for path in self.file_paths:
            base_name = os.path.splitext(os.path.basename(path))[0]
            filename = f"{base_name}_converted{ffmpeg_params['ext']}"
            if self.output_dir:
                output_path = os.path.join(self.output_dir, filename)
            else:
                output_path = os.path.join(os.path.dirname(path), filename)

            self.status_label.config(text=f"Конвертируется: {os.path.basename(path)}")
            self.log(f"=== Конвертация {os.path.basename(path)} ===\n")
            self.convert_file(path, output_path, ffmpeg_params, audio_stream_index)

        self.status_label.config(text="Конвертация завершена.")
        self.log("=== Конвертация завершена ===\n")
        self.open_output_folder()

    def start_conversion(self):
        thread = threading.Thread(target=self.conversion_thread)
        thread.start()

    def open_output_folder(self):
        if not self.file_paths:
            return

        folder_to_open = self.output_dir if self.output_dir else os.path.dirname(self.file_paths[0])

        try:
            if sys.platform == "win32":
                os.startfile(folder_to_open)  # Windows
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_to_open])  # macOS
            else:
                subprocess.Popen(["xdg-open", folder_to_open])  # Linux
        except Exception as e:
            messagebox.showwarning("Ошибка", f"Не удалось открыть папку:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FFmpegConverterApp(root)
    root.mainloop()