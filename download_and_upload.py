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

def fetch_playlist():
    base_url = "http://www.digimat.in/nptel/courses/video/106105234/106105234.html"
    req = urllib.request.Request(base_url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    
    items = []
    idx = 1
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        if href.endswith('.html') and href.startswith('L'):
            page_url = f"http://www.digimat.in/nptel/courses/video/106105234/{href}"
            standard_title = parse_title(text)
            week_num = get_week_number(idx)
            items.append({
                'idx': idx,
                'raw_title': text,
                'title': standard_title,
                'page_url': page_url,
                'week_num': week_num,
                'week_folder': WEEK_FOLDERS[week_num]
            })
            idx += 1
    return items

def get_yt_url(page_url):
    try:
        req = urllib.request.Request(page_url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        iframe = soup.find('iframe', src=lambda s: s and 'youtube.com' in s)
        if iframe:
            src = iframe['src']
            yt_id_match = re.search(r'embed/([a-zA-Z0-9_-]+)', src)
            if yt_id_match:
                return f"https://www.youtube.com/watch?v={yt_id_match.group(1)}"
    except Exception as e:
        print(f"Error fetching page {page_url}: {e}")
    return None

def download_video(yt_url, output_path):
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", output_path,
        yt_url
    ]
    res = subprocess.run(cmd)
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
    all_items = fetch_playlist()
    print(f"Fetched {len(all_items)} total lecture metadata items.")
    
    base_dir = os.path.abspath("downloads")
    os.makedirs(base_dir, exist_ok=True)
    
    for w in WEEK_ORDER:
        folder_name = WEEK_FOLDERS[w]
        local_week_dir = os.path.join(base_dir, folder_name)
        os.makedirs(local_week_dir, exist_ok=True)
        
        week_items = [item for item in all_items if item['week_num'] == w]
        print(f"\n==========================================")
        print(f"PROCESSING WEEK {w}: {folder_name} ({len(week_items)} items)")
        print(f"==========================================")
        
        for item in week_items:
            output_file = os.path.join(local_week_dir, f"{item['title']}.mp4")
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000000:
                print(f"[EXISTS] {output_file} already downloaded. Skipping download.")
                continue
            
            yt_url = get_yt_url(item['page_url'])
            if not yt_url:
                print(f"[ERROR] Could not extract YouTube URL for #{item['idx']}: {item['raw_title']}")
                continue
            
            print(f"\n--> Downloading #{item['idx']} [{item['title']}] from {yt_url}")
            success = download_video(yt_url, output_file)
            if not success:
                print(f"[RETRY] Attempting fallback download format for {item['title']}...")
                cmd_fallback = ["yt-dlp", "-o", output_file, yt_url]
                subprocess.run(cmd_fallback)
        
        # After completing the week's download, start uploading to Google Drive
        upload_success = upload_week_to_gdrive(local_week_dir, folder_name)
        if upload_success:
            print(f"[SUCCESS] Week {w} fully uploaded to Google Drive!")
        else:
            print(f"[WARNING] Week {w} upload encountered issues. Will continue next week.")

if __name__ == '__main__':
    process_pipeline()
