import os
import re
import sys
import time
import queue
import shutil
import threading
import subprocess
import urllib.request
import configparser
from bs4 import BeautifulSoup

WEEK_FOLDERS = {
    1: "Week1: Programming in C++ is Fun.",
    2: "Week2: C++ as Better C.",
    3: "Week3: OOP in C++.",
    4: "Week4: OOP in C++.",
    5: "Week5: Inheritance.",
    6: "Week6: Polymorphism.",
    7: "Week7: Type Casting.",
    8: "Week8: Exceptions and Templates.",
    9: "Week9: Streams and STL.",
    10: "Week10: Modern C++.",
    11: "Week11: Lambda and Concurrency.",
    12: "Week12: Move, Rvalue and STL Containers."
}

def load_config():
    config = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), "config.ini")
    if os.path.exists(config_file):
        config.read(config_file)
    return config

def get_week_number(item_idx):
    if item_idx <= 66:
        return (item_idx - 1) // 6 + 1
    else:
        return 12

def parse_title(raw_title):
    clean_name = raw_title.strip()
    clean_name = clean_name.replace('/', '-').replace(':', '-')
    clean_name = re.sub(r'\s+', ' ', clean_name)
    clean_name = re.sub(r'-\s*-', '-', clean_name).strip()
    return clean_name

def fetch_playlist_items():
    base_url = "http://www.digimat.in/nptel/courses/video/106105234/106105234.html"
    req = urllib.request.Request(base_url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    
    title_map = {}
    idx = 1
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        if href.endswith('.html') and href.startswith('L'):
            title_map[idx] = parse_title(text)
            idx += 1
            
    items = []
    video_tags = soup.find_all('video')
    
    for idx, v in enumerate(video_tags, 1):
        source = v.find('source')
        mp4_url = source.get('src') if source else None
        
        raw_title = title_map.get(idx, f"Lecture {idx}")
        week_num = get_week_number(idx)
        formatted_filename = f"{idx:02d} - {raw_title}.mp4"
        
        items.append({
            'idx': idx,
            'title': raw_title,
            'filename': formatted_filename,
            'mp4_url': mp4_url,
            'week_num': week_num,
            'week_folder': WEEK_FOLDERS[week_num]
        })
        
    return items

def download_file(url, target_path, retries=5):
    for attempt in range(1, retries + 1):
        print(f"[DOWNLOADING] {os.path.basename(target_path)} (Attempt {attempt}/{retries})")
        cmd_curl = [
            "curl", "-s", "-L", "-C", "-",
            "--connect-timeout", "15",
            "--max-time", "300",
            "--retry", "5",
            "--retry-delay", "2",
            "-o", target_path, url
        ]
        res = subprocess.run(cmd_curl)
        if res.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 1000000:
            return True
        time.sleep(2)
    return False

def upload_single_file(local_path, remote_week_folder, gdrive_remote_root):
    if not shutil.which("rclone"):
        print("[ERROR] 'rclone' executable is not installed or not found on PATH!")
        return False
    remote_target = f"{gdrive_remote_root}/{remote_week_folder}"
    print(f"[UPLOADING] {os.path.basename(local_path)} -> {remote_target}")
    cmd = [
        "rclone", "copy",
        local_path,
        remote_target,
        "--drive-chunk-size", "64M",
        "--stats", "0"
    ]
    res = subprocess.run(cmd)
    return res.returncode == 0

def process_pipeline():
    config = load_config()
    base_dir = config.get("GENERAL", "base_storage_dir", fallback="./downloads")
    gdrive_root = config.get("GENERAL", "gdrive_remote_root", fallback="gdrive:NPTEL Modern C++")
    do_upload = config.getboolean("GENERAL", "upload_to_gdrive", fallback=True)
    delete_after_upload = config.getboolean("GENERAL", "delete_after_upload", fallback=True)
    
    num_download_workers = config.getint("GENERAL", "download_workers", fallback=1)
    num_upload_workers = config.getint("GENERAL", "upload_workers", fallback=2)
    max_queue_size = 3  # Never allow more than 3 downloaded files to pile up in RAM/Disk

    raw_week_order = config.get("PIPELINE", "week_order", fallback="1,2,3,4,5,6,7,8,9,10,11,12")
    week_order = [int(w.strip()) for w in raw_week_order.split(",") if w.strip().isdigit()]

    all_items = fetch_playlist_items()
    print(f"Fetched {len(all_items)} total direct MP4 items.")
    os.makedirs(base_dir, exist_ok=True)

    # 1. PHASE 1: UPLOAD AND DELETE ALL PRE-EXISTING LOCAL FILES FIRST
    print("\n==========================================")
    print("PHASE 1: UPLOADING AND DELETING ALL PRE-EXISTING LOCAL FILES FIRST")
    print("==========================================")
    for root, dirs, files in os.walk(base_dir):
        for fname in sorted(files):
            if fname.endswith(".mp4") and not fname.endswith(".raw.mp4"):
                local_filepath = os.path.join(root, fname)
                if os.path.getsize(local_filepath) > 1000000:
                    folder_name = os.path.basename(root)
                    print(f"\n[FOUND LOCAL FILE] {fname} in '{folder_name}'")
                    if do_upload:
                        upload_success = upload_single_file(local_filepath, folder_name, gdrive_root)
                        if upload_success:
                            print(f"[UPLOAD SUCCESS] {fname}")
                            if delete_after_upload and os.path.exists(local_filepath):
                                os.remove(local_filepath)
                                print(f"[CLEANUP] Deleted local file: {fname}")

    # 2. PHASE 2: STREAM PIPELINE WITH BOUNDED UPLOAD QUEUE & SPEED BACKPRESSURE
    print("\n==========================================")
    print("PHASE 2: STREAMING PIPELINE WITH SPEED BACKPRESSURE CONTROL")
    print("==========================================")

    download_queue = queue.Queue()
    upload_queue = queue.Queue(maxsize=max_queue_size)
    failed_items = []
    failed_lock = threading.Lock()

    for w in week_order:
        if w not in WEEK_FOLDERS:
            continue
        folder_name = WEEK_FOLDERS[w]
        local_week_dir = os.path.join(base_dir, folder_name)
        os.makedirs(local_week_dir, exist_ok=True)
        
        week_items = [item for item in all_items if item['week_num'] == w]
        for item in week_items:
            output_file = os.path.join(local_week_dir, item['filename'])
            if not (os.path.exists(output_file) and os.path.getsize(output_file) > 1000000):
                download_queue.put((item, output_file, folder_name))

    active_downloads_lock = threading.Lock()
    active_downloads_count = 0

    def download_worker():
        nonlocal active_downloads_count
        while True:
            try:
                item, output_file, folder_name = download_queue.get_nowait()
            except queue.Empty:
                break
            
            with active_downloads_lock:
                active_downloads_count += 1

            mp4_url = item['mp4_url']
            if mp4_url:
                success = download_file(mp4_url, output_file)
                if success:
                    print(f"[DOWNLOAD COMPLETE] #{item['idx']:02d} [{item['filename']}]")
                    if do_upload:
                        # Put will block if upload_queue reaches maxsize (3 files), pausing download automatically
                        upload_queue.put((output_file, folder_name))
                else:
                    print(f"[DOWNLOAD FAILED] #{item['idx']:02d} [{item['filename']}] - queued for retry pass.")
                    with failed_lock:
                        failed_items.append((item, output_file, folder_name))
            
            with active_downloads_lock:
                active_downloads_count -= 1
            
            download_queue.task_done()

    def upload_worker():
        while True:
            try:
                local_filepath, folder_name = upload_queue.get(timeout=3)
            except queue.Empty:
                with active_downloads_lock:
                    is_active = active_downloads_count > 0
                if download_queue.empty() and not is_active:
                    break
                continue
            
            fname = os.path.basename(local_filepath)
            upload_success = upload_single_file(local_filepath, folder_name, gdrive_root)
            if upload_success:
                print(f"[UPLOAD SUCCESS] {fname}")
                if delete_after_upload and os.path.exists(local_filepath):
                    os.remove(local_filepath)
                    print(f"[CLEANUP] Deleted local file: {fname}")
            else:
                print(f"[UPLOAD WARNING] Failed to upload {fname}")
            upload_queue.task_done()

    upload_threads = []
    for _ in range(num_upload_workers):
        t = threading.Thread(target=upload_worker)
        t.daemon = True
        t.start()
        upload_threads.append(t)

    download_threads = []
    for _ in range(num_download_workers):
        t = threading.Thread(target=download_worker)
        t.start()
        download_threads.append(t)

    for t in download_threads:
        t.join()

    download_queue.join()
    upload_queue.join()

    # 3. PHASE 3: RETRY FAILED DOWNLOADS AT THE END
    if failed_items:
        print("\n==========================================")
        print(f"PHASE 3: RETRYING {len(failed_items)} FAILED DOWNLOADS")
        print("==========================================")
        for item, output_file, folder_name in failed_items:
            print(f"\n--> Retrying #{item['idx']:02d} [{item['filename']}]")
            success = download_file(item['mp4_url'], output_file, retries=10)
            if success and do_upload:
                upload_success = upload_single_file(output_file, folder_name, gdrive_root)
                if upload_success and delete_after_upload and os.path.exists(output_file):
                    os.remove(output_file)

    print("\n[COMPLETE] All downloads and uploads finished successfully!")

if __name__ == '__main__':
    process_pipeline()
