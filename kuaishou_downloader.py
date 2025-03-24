import requests
import os
from urllib.parse import urlparse
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import webbrowser
import threading
import io
import json

default_save_dir = ""
selected_videos = []
progress_bars = {}

# Giá trị mặc định cho headers và cookies
default_headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
    "Connection": "keep-alive",
}

default_cookies = {
    "did": "web_cc52f9dba12c4e62bc5a2e5bff8fc3eb",
    "didv": "1742744135000",
    "kuaishou.live.bfb1s": "ac5f27b3b62895859c4c1622f49856a4",
    "clientid": "3",
    "client_key": "65890b29",
    "kpn": "GAME_ZONE",
    "kwpsecproductname": "PCLive",
    "kwscode": "8aad2d2b324d894df87afb11e3e354954b83d602bf936b28b41ffd3a68336160",
    "kwssectoken": "5cys+yX+4qtniDYUI91IJaTbVPwbaYEg0hyhy47Rqr49arutpTd44zv9gFHRYEvN4Y7K7FZqz9UBsAGGzHBJLg==",
    "kwfv1": "PeDA80mSG00ZF8e400wnrU+fr78fLAwn+f+erh8nz0Pfbf+fbS8e8f+erEGA40+epf+nbS8emSP0cMGfb08Bbf8eG98/8D+eQSw/PF8ncUGnr98fbj+AHlPeLAPnzYwnr78fLFP/bj+A+0w/PAPA+0+/q9wn+SPechG0zjPnpfP9G="
}

# Biến toàn cục để lưu headers và cookies tùy chỉnh
current_headers = default_headers.copy()
current_cookies = default_cookies.copy()

def parse_profile_url(url, count):
    parsed_url = urlparse(url)
    principal_id = parsed_url.path.split('/')[-1]
    api_url = f"https://live.kuaishou.com/live_api/profile/public?count={count}&pcursor=&principalId={principal_id}&hasMore=true"
    return api_url

def download_video(play_url, video_id, save_path, progress_bar):
    response = requests.get(play_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0

    if response.status_code == 200:
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded_size += len(chunk)
                    f.write(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        progress_bar['value'] = progress
                        root.update_idletasks()
        return f"Đã tải xong: {os.path.basename(save_path)}"
    else:
        return f"Lỗi khi tải video {video_id}: {response.status_code}"

def fetch_videos(profile_url, count, callback):
    if not profile_url:
        messagebox.showerror("Lỗi", "Vui lòng cung cấp URL profile!")
        return

    submit_btn.config(state="disabled")
    loading_label.config(text="Đang tải...")
    root.update()

    try:
        api_url = parse_profile_url(profile_url, count)
    except Exception as e:
        messagebox.showerror("Lỗi", f"Lỗi khi phân tích URL: {e}")
        loading_label.config(text="")
        submit_btn.config(state="normal")
        return

    headers = current_headers.copy()
    headers["Referer"] = profile_url  # Đảm bảo Referer luôn là profile_url
    cookies = current_cookies.copy()

    response = requests.get(api_url, headers=headers, cookies=cookies)
    if response.status_code == 200:
        try:
            data = response.json()
            video_list = data.get("data", {}).get("list", [])
            if not video_list:
                messagebox.showinfo("Thông báo", "Không tìm thấy video nào!")
                loading_label.config(text="")
                submit_btn.config(state="normal")
                return
            callback(video_list)
        except requests.exceptions.JSONDecodeError:
            messagebox.showerror("Lỗi", "Không thể phân tích dữ liệu API!")
    else:
        messagebox.showerror("Lỗi", f"Lỗi khi truy cập API: {response.status_code}")

    loading_label.config(text="")
    submit_btn.config(state="normal")

def load_image(url, size=(100, 100)):
    response = requests.get(url)
    img_data = response.content
    img = Image.open(io.BytesIO(img_data))
    img = img.resize(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img)

def display_videos(video_list):
    global selected_videos, progress_bars
    selected_videos = []
    progress_bars = {}
    for widget in video_frame.winfo_children():
        widget.destroy()

    row, col = 0, 0
    max_cols = 8

    for video in video_list:
        video_id = video.get("id", "unknown")
        poster_url = video.get("poster", "")
        play_url = video.get("playUrl", "")

        frame = tk.Frame(video_frame, borderwidth=1, relief="solid", pady=5, padx=5)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        var = tk.BooleanVar()
        checkbox = tk.Checkbutton(frame, variable=var,
                                  command=lambda v=var, u=play_url, i=video_id: update_selected_videos(v, u, i))
        checkbox.pack(pady=2)

        if poster_url:
            poster_img = load_image(poster_url)
            poster_label = tk.Label(frame, image=poster_img)
            poster_label.image = poster_img
            poster_label.pack(pady=2)

        def download_single_thread(play_url, video_id, progress_bar):
            if not default_save_dir:
                messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu trữ trước!")
                return
            save_path = os.path.join(default_save_dir, f"{video_id}.mp4")
            result = download_video(play_url, video_id, save_path, progress_bar)
            messagebox.showinfo("Kết quả", result)

        progress_bar = ttk.Progressbar(frame, length=100, mode='determinate')
        progress_bar.pack(pady=2)
        progress_bars[video_id] = progress_bar

        download_btn = tk.Button(frame, text="Download",
                                 command=lambda url=play_url, vid=video_id, pb=progress_bar: threading.Thread(
                                     target=download_single_thread, args=(url, vid, pb), daemon=True).start())
        download_btn.pack(pady=2)

        view_btn = tk.Button(frame, text="Xem Video",
                             command=lambda url=play_url: webbrowser.open(url))
        view_btn.pack(pady=2)

        info_label = tk.Label(frame, text=f"ID: {video_id}")
        info_label.pack(pady=2)

        col += 1
        if col >= max_cols:
            col = 0
            row += 1

def update_selected_videos(var, play_url, video_id):
    global selected_videos
    video_info = (play_url, video_id)
    if var.get():
        if video_info not in selected_videos:
            selected_videos.append(video_info)
    else:
        if video_info in selected_videos:
            selected_videos.remove(video_info)

def download_selected_videos():
    if not default_save_dir:
        messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu trữ trước!")
        return
    if not selected_videos:
        messagebox.showerror("Lỗi", "Vui lòng chọn ít nhất một video để tải!")
        return

    def download_all():
        download_all_btn.config(state="disabled")
        loading_label.config(text="Đang tải tất cả video...")
        root.update_idletasks()

        for play_url, video_id in selected_videos:
            save_path = os.path.join(default_save_dir, f"{video_id}.mp4")
            progress_bar = progress_bars.get(video_id)
            if progress_bar:
                result = download_video(play_url, video_id, save_path, progress_bar)
                print(result)

        download_all_btn.config(state="normal")
        loading_label.config(text="")
        messagebox.showinfo("Hoàn tất", "Đã tải xong tất cả video đã chọn!")

    threading.Thread(target=download_all, daemon=True).start()

def show_config_popup():
    popup = tk.Toplevel(root)
    popup.title("Cấu hình Headers và Cookies")
    popup.geometry("600x400")
    popup.transient(root)
    popup.grab_set()

    # Headers
    tk.Label(popup, text="Headers (JSON):").pack(pady=5)
    headers_text = tk.Text(popup, height=5, width=60)
    headers_text.pack(pady=2)
    headers_text.insert(tk.END, json.dumps(current_headers, indent=2))

    # Cookies
    tk.Label(popup, text="Cookies (JSON):").pack(pady=5)
    cookies_text = tk.Text(popup, height=5, width=60)
    cookies_text.pack(pady=2)
    cookies_text.insert(tk.END, json.dumps(current_cookies, indent=2))

    def submit_config():
        global current_headers, current_cookies
        try:
            headers_input = headers_text.get("1.0", tk.END).strip()
            cookies_input = cookies_text.get("1.0", tk.END).strip()
            current_headers = json.loads(headers_input) if headers_input else default_headers
            current_cookies = json.loads(cookies_input) if cookies_input else default_cookies
            popup.destroy()
            messagebox.showinfo("Thành công", "Đã cập nhật headers và cookies!")
        except json.JSONDecodeError:
            messagebox.showerror("Lỗi", "Headers hoặc Cookies không đúng định dạng JSON!")

    tk.Button(popup, text="Xác nhận", command=submit_config).pack(pady=10)

def on_submit():
    profile_url = url_entry.get()
    count_input = count_entry.get().strip()
    try:
        count = int(count_input) if count_input else 100  # Giá trị mặc định là 100
        if count <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Lỗi", "Số lượng video phải là một số nguyên dương!")
        return
    threading.Thread(target=fetch_videos, args=(profile_url, count, display_videos), daemon=True).start()

def select_save_directory():
    global default_save_dir
    default_save_dir = filedialog.askdirectory()
    if default_save_dir:
        save_dir_label.config(text=f"Thư mục lưu: {default_save_dir}")
    else:
        save_dir_label.config(text="Thư mục lưu: Chưa chọn")

# Tạo giao diện GUI
root = tk.Tk()
root.title("Kuaishou Video Downloader")
root.geometry("1000x800")

# Frame cho URL, số lượng video và nút submit
url_frame = tk.Frame(root)
url_frame.pack(pady=5)
tk.Label(url_frame, text="Nhập URL Profile:").pack(side="left")
url_entry = tk.Entry(url_frame, width=50)
url_entry.pack(side="left", padx=5)
tk.Label(url_frame, text="Số lượng video:").pack(side="left")
count_entry = tk.Entry(url_frame, width=10)
count_entry.insert(0, "100")  # Đặt giá trị mặc định là 100
count_entry.pack(side="left", padx=5)
submit_btn = tk.Button(url_frame, text="Submit", command=on_submit)
submit_btn.pack(side="left")

# Frame cho chọn thư mục lưu trữ
save_frame = tk.Frame(root)
save_frame.pack(pady=5)
tk.Button(save_frame, text="Chọn thư mục lưu trữ", command=select_save_directory).pack(side="left", padx=5)
save_dir_label = tk.Label(save_frame, text="Thư mục lưu: Chưa chọn")
save_dir_label.pack(side="left")

# Nút Config ở góc phải trên
top_right_frame = tk.Frame(root)
top_right_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
tk.Button(top_right_frame, text="Config", command=show_config_popup).pack(side="left", padx=5)

# Nút tải hàng loạt
download_all_btn = tk.Button(root, text="Tải các video đã chọn", command=download_selected_videos)
download_all_btn.pack(pady=5)

# Label hiển thị trạng thái tải
loading_label = tk.Label(root, text="")
loading_label.pack()

# Frame chứa danh sách video với scrollbar
canvas = tk.Canvas(root)
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

video_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=video_frame, anchor="nw")

def configure_scroll(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

video_frame.bind("<Configure>", configure_scroll)

root.mainloop()