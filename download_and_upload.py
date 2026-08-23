import os
import re
import sys
import time
import subprocess
import urllib.request
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

# Target execution order: Weeks 3 through 12 first, then Weeks 1 and 2
WEEK_ORDER = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2]

GDRIVE_REMOTE_ROOT = "gdrive:NPTEL Modern C++"
BASE_STORAGE_DIR = "/mnt/storage/nptel_downloads"

def get_week_number(item_idx):
    if item_idx <= 66:
        return (item_idx - 1) // 6 + 1
    else:
        return 12

def parse_title(raw_title):
    tut_match = re.search(r'Tutorial\s*(\d+)\s*:\s*(.*)', raw_title, re.IGNORECASE)
    if tut_match:
        tut_num = tut_match.group(1)
        rest = tut_match.group(2).strip()
        clean_name = f"T{tut_num} - {rest}"
    else:
        lec_match = re.search(r'Lecture\s*(\d+)\s*-\s*(.*)', raw_title, re.IGNORECASE)
        if lec_match:
            lec_num = lec_match.group(1)
            rest = lec_match.group(2).strip()
            clean_name = f"L{lec_num} - {rest}"
        else:
            clean_name = raw_title.strip()
    
    clean_name = clean_name.replace('/', '-').replace(':', '-')
    clean_name = re.sub(r'\s+', ' ', clean_name)
    clean_name = re.sub(r'-\s*-', '-', clean_name).strip()
    return clean_name

def fetch_titles_from_main_html():
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
    return title_map

def fetch_direct_mp4_playlist():
    base_url = "http://www.digimat.in/nptel/courses/video/106105234/106105234.html"
    req = urllib.request.Request(base_url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    
    title_map = fetch_titles_from_main_html()
    items = []
    video_tags = soup.find_all('video')
    
    for idx, v in enumerate(video_tags, 1):
        source = v.find('source')
        mp4_url = source.get('src') if source else None
        
        standard_title = title_map.get(idx, f"L{idx} - Lecture {idx}")
        week_num = get_week_number(idx)
        
        items.append({
            'idx': idx,
            'title': standard_title,
            'mp4_url': mp4_url,
            'week_num': week_num,
            'week_folder': WEEK_FOLDERS[week_num]
        })
        
    return items

def download_file(url, output_path):
    print(f"Downloading direct MP4: {url}")
    cmd = [
        "aria2c", "-x", "16", "-s", "16", "-k", "1M",
        "-o", os.path.basename(output_path),
        "-d", os.path.dirname(output_path),
        url
    ]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("[FALLBACK] Using curl for download...")
        cmd_curl = ["curl", "-L", "-C", "-", "-o", output_path, url]
        res = subprocess.run(cmd_curl)
    return res.returncode == 0

def upload_week_to_gdrive(local_week_dir, remote_folder_name):
    remote_target = f"{GDRIVE_REMOTE_ROOT}/{remote_folder_name}"
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
    all_items = fetch_direct_mp4_playlist()
    print(f"Fetched {len(all_items)} total direct MP4 items.")
    
    os.makedirs(BASE_STORAGE_DIR, exist_ok=True)
    
    for w in WEEK_ORDER:
        folder_name = WEEK_FOLDERS[w]
        local_week_dir = os.path.join(BASE_STORAGE_DIR, folder_name)
        os.makedirs(local_week_dir, exist_ok=True)
        
        week_items = [item for item in all_items if item['week_num'] == w]
        print(f"\n==========================================")
        print(f"PROCESSING WEEK {w}: {folder_name} ({len(week_items)} items)")
        print(f"==========================================")
        
        for item in week_items:
            output_file = os.path.join(local_week_dir, f"{item['title']}.mp4")
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000000:
                print(f"[EXISTS] {output_file} already downloaded. Skipping.")
                continue
            
            mp4_url = item['mp4_url']
            if not mp4_url:
                print(f"[ERROR] Could not extract direct MP4 URL for #{item['idx']}: {item['title']}")
                continue
            
            print(f"\n--> Downloading #{item['idx']} [{item['title']}]")
            download_file(mp4_url, output_file)
        
        upload_success = upload_week_to_gdrive(local_week_dir, folder_name)
        if upload_success:
            print(f"[SUCCESS] Week {w} fully uploaded to Google Drive!")
        else:
            print(f"[WARNING] Week {w} upload encountered issues.")

if __name__ == '__main__':
    process_pipeline()
