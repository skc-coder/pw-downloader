import os
import re
import sys
import time
import subprocess
import urllib.request
import configparser
from bs4 import BeautifulSoup

# Define folders mapping matching Digimat 75-lecture curriculum structure:
# Weeks 1 to 11 have 6 lectures each (75 - 66 = 9 for Week 12).
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
    # Standardize titles for filenames
    # Clean up slashes, colons, duplicate hyphens and spaces
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
    
    # Map item index to cleaned title
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

        # Accurate 2-digit zero-padded index (01 to 75)
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

def download_and_boost_volume(url, final_output_path):
    temp_raw_path = final_output_path + ".raw.mp4"
    print(f"Downloading direct MP4: {url}")
    cmd_curl = ["curl", "-L", "-C", "-", "-o", temp_raw_path, url]
    res = subprocess.run(cmd_curl)
    if res.returncode != 0:
        print(f"[ERROR] Failed to download MP4 for {final_output_path}")
        return False
    
    print(f"Boosting volume (2.0x / +6dB) via ffmpeg...")
    cmd_ffmpeg = [
        "ffmpeg", "-y",
        "-i", temp_raw_path,
        "-c:v", "copy",
        "-filter:a", "volume=2.0",
        final_output_path
    ]
    res_ff = subprocess.run(cmd_ffmpeg)
    
    if res_ff.returncode == 0 and os.path.exists(final_output_path):
        if os.path.exists(temp_raw_path):
            os.remove(temp_raw_path)
        return True
    else:
        print("[WARNING] ffmpeg volume boost failed, keeping original audio/video file...")
        if os.path.exists(temp_raw_path):
            os.rename(temp_raw_path, final_output_path)
            return True
        return False

def upload_week_to_gdrive(local_week_dir, remote_folder_name, gdrive_remote_root):
    remote_target = f"{gdrive_remote_root}/{remote_folder_name}"
    print(f"\n==========================================")
    print(f"Uploading {local_week_dir} -> {remote_target}")
    print(f"==========================================")
    cmd = [
        "rclone", "copy",
        local_week_dir,
        remote_target,
        "--progress",
        "--stats", "5s"
    ]
    res = subprocess.run(cmd)
    return res.returncode == 0

def process_pipeline():
    config = load_config()
    base_dir = config.get("GENERAL", "base_storage_dir", fallback="./downloads")
    gdrive_root = config.get("GENERAL", "gdrive_remote_root", fallback="gdrive:NPTEL Modern C++")
    do_upload = config.getboolean("GENERAL", "upload_to_gdrive", fallback=False)
    
    raw_week_order = config.get("PIPELINE", "week_order", fallback="1,2,3,4,5,6,7,8,9,10,11,12")
    week_order = [int(w.strip()) for w in raw_week_order.split(",") if w.strip().isdigit()]

    all_items = fetch_playlist_items()
    print(f"Fetched {len(all_items)} total direct MP4 items.")
    
    os.makedirs(base_dir, exist_ok=True)
    
    for w in week_order:
        if w not in WEEK_FOLDERS:
            continue
        folder_name = WEEK_FOLDERS[w]
        local_week_dir = os.path.join(base_dir, folder_name)
        os.makedirs(local_week_dir, exist_ok=True)
        
        week_items = [item for item in all_items if item['week_num'] == w]
        print(f"\n==========================================")
        print(f"PROCESSING WEEK {w}: {folder_name} ({len(week_items)} items)")
        print(f"==========================================")
        
        for item in week_items:
            output_file = os.path.join(local_week_dir, item['filename'])
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000000:
                print(f"[EXISTS] {item['filename']} already processed. Skipping.")
                continue
            
            mp4_url = item['mp4_url']
            if not mp4_url:
                print(f"[ERROR] Could not extract direct MP4 URL for #{item['idx']}: {item['filename']}")
                continue
            
            print(f"\n--> Processing #{item['idx']:02d} [{item['filename']}]")
            download_and_boost_volume(mp4_url, output_file)
        
        if do_upload:
            upload_success = upload_week_to_gdrive(local_week_dir, folder_name, gdrive_root)
            if upload_success:
                print(f"[SUCCESS] Week {w} fully uploaded to Google Drive!")
            else:
                print(f"[WARNING] Week {w} upload encountered issues.")

if __name__ == '__main__':
    process_pipeline()
