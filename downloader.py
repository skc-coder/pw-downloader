import os
import re
import sys
import time
import subprocess
import urllib.request
from bs4 import BeautifulSoup

# Define folders mapping exactly as requested by the user:
# Week1: Programming in C++ is Fun.
# Week2: C++ as Better C.
# Week3: OOP in C++.
# Week4: OOP in C++.
# Week5: Inheritance.
# Week6: Polymorphism.
# Week7: Type Casting.
# Week8: Exceptions and Templates.
# Week9: Streams and STL.
# Week10: Modern C++.
# Week11: Lambda and Concurrency.
# Week12: Move, Rvalue and STL Containers.

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

# 75 items total -> 6 items per week for weeks 1-11, 9 items for week 12
# Week 1: 1-6
# Week 2: 7-12
# Week 3: 13-18
# Week 4: 19-24
# Week 5: 25-30
# Week 6: 31-36
# Week 7: 37-42
# Week 8: 43-48
# Week 9: 49-54
# Week 10: 55-60
# Week 11: 61-66
# Week 12: 67-75

def get_week_number(item_idx):
    if item_idx <= 66:
        return (item_idx - 1) // 6 + 1
    else:
        return 12

def parse_title(raw_title):
    # Standardize video titles:
    # "Lecture 1 - Course Outline" -> "L1 - Course Outline"
    # "Lecture 9 - Tutorial 1: How to build..." -> "T1 - How to build..."
    # "Lecture 15 - Tutorial 2: ..." -> "T2 - ..."
    # Clean up whitespace and special characters safe for filenames.
    
    # Check if title contains Tutorial
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
    
    # Sanitize for filesystem/drive (avoid slashes, colons if problematic)
    clean_name = clean_name.replace('/', '-').replace(':', '-')
    # remove duplicate dashes/spaces
    clean_name = re.sub(r'\s+', ' ', clean_name)
    clean_name = re.sub(r'-\s*-', '-', clean_name)
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
    req = urllib.request.Request(page_url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    iframe = soup.find('iframe', src=lambda s: s and 'youtube.com' in s)
    if iframe:
        src = iframe['src']
        yt_id_match = re.search(r'embed/([a-zA-Z0-9_-]+)', src)
        if yt_id_match:
            return f"https://www.youtube.com/watch?v={yt_id_match.group(1)}"
    return None

if __name__ == '__main__':
    items = fetch_playlist()
    print(f"Total lectures found: {len(items)}")
    for item in items[:10]:
        print(f"Week {item['week_num']} [{item['week_folder']}] -> #{item['idx']}: {item['title']}")
