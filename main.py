import requests
import os
from urllib.parse import urlparse

def parse_profile_url(url):
    """Phân tích URL để lấy principalId và tạo api_url"""
    parsed_url = urlparse(url)
    principal_id = parsed_url.path.split('/')[-1]  # Lấy principalId từ path
    api_url = f"https://live.kuaishou.com/live_api/profile/public?count=50&pcursor=&principalId={principal_id}&hasMore=true"
    return api_url

def download_videos(profile_url):
    if not profile_url:
        print("Lỗi: Vui lòng cung cấp URL profile!")
        return

    # Phân tích URL để tạo api_url
    try:
        api_url = parse_profile_url(profile_url)
        print(f"API URL được tạo: {api_url}")
    except Exception as e:
        print(f"Lỗi khi phân tích URL: {e}")
        return

    # Headers mặc định
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": profile_url,  # Dùng URL profile làm Referer
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
        "Connection": "keep-alive",
    }

    # Cookies mặc định (có thể cần cập nhật)
    cookies = {
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

    download_folder = "downloaded_videos"
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    print("Đang gửi yêu cầu tới API...")
    response = requests.get(api_url, headers=headers, cookies=cookies)
    if response.status_code == 200:
        try:
            data = response.json()
            video_list = data.get("data", {}).get("list", [])
            if not video_list:
                print("Không tìm thấy video nào trong danh sách!")
                return
            for video in video_list:
                video_id = video.get("id", "unknown")
                play_url = video.get("playUrl", "")
                if play_url:
                    print(f"Đang tải video: {video_id}")
                    video_response = requests.get(play_url, stream=True)
                    if video_response.status_code == 200:
                        file_name = f"{video_id}.mp4"
                        file_path = os.path.join(download_folder, file_name)
                        with open(file_path, "wb") as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        print(f"Đã tải xong: {file_name}")
                    else:
                        print(f"Lỗi khi tải video {video_id}: {video_response.status_code}")
                else:
                    print(f"Không tìm thấy playUrl cho video {video_id}")
            print("Hoàn tất quá trình tải!")
        except requests.exceptions.JSONDecodeError:
            print("Lỗi: Không thể phân tích dữ liệu API! Phản hồi không phải JSON hợp lệ.")
            print(f"Phản hồi từ API: {response.text[:500]}")
    else:
        print(f"Lỗi khi truy cập API: {response.status_code}")
        print(f"Phản hồi từ API: {response.text[:500]}")

if __name__ == "__main__":
    # Nhập URL từ console
    profile_url = input("Nhập URL profile Kuaishou: ")
    download_videos(profile_url)