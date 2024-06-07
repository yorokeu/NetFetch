import tkinter as tk
from tkinter import ttk
import requests
import threading
import os
import time
from urllib.parse import urlparse
from math import floor
from ttkthemes import ThemedStyle

class DownloadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Downloader")
        self.root.geometry("600x400")

        self.style = ThemedStyle(self.root)
        self.style.set_theme("arc")

        self.create_widgets()

        self.download_folder = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        
        self.download_thread = None
        self.pause_flag = False
        self.resume_flag = threading.Event()
        self.resume_flag.set()
        self.stop_flag = False

    def create_widgets(self):
        # Create main frames
        self.frame_top = ttk.Frame(self.root, padding="10 10 10 10")
        self.frame_top.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.frame_bottom = ttk.Frame(self.root, padding="10 10 10 10")
        self.frame_bottom.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure top frame
        self.url_label = ttk.Label(self.frame_top, text="Enter URL:")
        self.url_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.url_entry = ttk.Entry(self.frame_top, width=70)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        self.start_button = ttk.Button(self.frame_top, text="Start", command=self.start_download)
        self.start_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.status_label = ttk.Label(self.frame_top, text="Status: Not started")
        self.status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        self.progress = ttk.Progressbar(self.frame_top, orient='horizontal', length=500, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))

        self.pause_button = ttk.Button(self.frame_top, text="Pause", command=self.pause_download, state=tk.DISABLED)
        self.pause_button.grid(row=3, column=1, padx=5, pady=5, sticky=tk.E)

        self.cancel_button = ttk.Button(self.frame_top, text="Cancel", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_button.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)

        # Configure bottom frame
        self.details_label = ttk.Label(self.frame_bottom, text="Details:")
        self.details_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        columns = ('#1', '#2', '#3')
        self.tree = ttk.Treeview(self.frame_bottom, columns=columns, show='headings')
        self.tree.heading('#1', text='No.')
        self.tree.heading('#2', text='Downloaded')
        self.tree.heading('#3', text='Info')

        self.tree.column('#1', width=50, anchor=tk.CENTER)
        self.tree.column('#2', width=150, anchor=tk.CENTER)
        self.tree.column('#3', width=300, anchor=tk.W)

        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.frame_bottom.rowconfigure(1, weight=1)
        self.frame_bottom.columnconfigure(0, weight=1)

    def start_download(self):
        url = self.url_entry.get()
        if url:
            self.url_entry.config(state=tk.DISABLED)
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)
            self.status_label.config(text="Status: Downloading...")
            self.download_thread = threading.Thread(target=self.download_file, args=(url,))
            self.download_thread.start()

    def pause_download(self):
        if self.pause_button['text'] == "Pause":
            self.pause_flag = True
            self.resume_flag.clear()
            self.pause_button.config(text="Resume")
        else:
            self.pause_flag = False
            self.resume_flag.set()
            self.pause_button.config(text="Pause")

    def cancel_download(self):
        self.stop_flag = True
        self.resume_flag.set()
        self.pause_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Download canceled.")
        self.url_entry.config(state=tk.NORMAL)
        self.start_button.config(state=tk.NORMAL)

    def download_file(self, url):
        local_filename = os.path.join(self.download_folder, os.path.basename(urlparse(url).path))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # طلب بيانات الملف والتحقق من حالة الاستجابة
        r = requests.get(url, headers=headers, stream=True)
        if r.status_code == 403:
            self.status_label.config(text="Error: Access forbidden (403).")
            self.url_entry.config(state=tk.NORMAL)
            self.start_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            return
        if r.status_code != 200:
            self.status_label.config(text=f"Error: Failed to retrieve file. Status code: {r.status_code}")
            self.url_entry.config(state=tk.NORMAL)
            self.start_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            return
        
        total_size = int(r.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        wrote = 0

        start_time = time.time()

        with open(local_filename, 'wb') as f:
            for i, data in enumerate(r.iter_content(block_size)):
                if self.stop_flag:
                    break
                while self.pause_flag:
                    self.resume_flag.wait()
                wrote += len(data)
                f.write(data)
                self.update_status(local_filename, total_size, wrote, start_time, i)
                if total_size > 0:
                    self.progress['value'] = (wrote / total_size) * 100
        
        if self.stop_flag:
            os.remove(local_filename)
            self.status_label.config(text="Status: Download canceled.")
        elif total_size != 0 and wrote < total_size:
            self.status_label.config(text=f"Error: Download incomplete. Only {self.human_readable_size(wrote)} of {self.human_readable_size(total_size)} downloaded.")
        else:
            self.status_label.config(text=f"Download complete: {local_filename}")

        self.pause_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        self.url_entry.config(state=tk.NORMAL)
        self.start_button.config(state=tk.NORMAL)
        self.stop_flag = False

    def update_status(self, filename, total_size, wrote, start_time, block_num):
        elapsed_time = time.time() - start_time
        download_speed = wrote / elapsed_time if elapsed_time > 0 else 0
        remaining_time = (total_size - wrote) / download_speed if download_speed > 0 else 0
        
        percent = (wrote / total_size) * 100 if total_size > 0 else 100
        
        self.root.title(f"{percent:.2f}% - {os.path.basename(filename)}")

        self.status_label.config(text=(
            f"File size: {self.human_readable_size(total_size)}\n"
            f"Downloaded: {self.human_readable_size(wrote)} / {self.human_readable_size(total_size)} "
            f"({percent:.2f}%)\n"
            f"Transfer rate: {self.human_readable_size(download_speed)}/s\n"
            f"Time left: {self.human_readable_time(remaining_time)}\n"
            f"Resume capability: Yes"
        ))

        # Update tree view
        self.tree.insert('', 'end', values=(block_num + 1, self.human_readable_size(wrote), "Receiving data..."))

    def human_readable_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024

    def human_readable_time(self, seconds):
        days = floor(seconds / (24 * 3600))
        seconds %= (24 * 3600)
        hours = floor(seconds / 3600)
        seconds %= 3600
        minutes = floor(seconds / 60)
        seconds = floor(seconds % 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloadApp(root)
    root.mainloop()
