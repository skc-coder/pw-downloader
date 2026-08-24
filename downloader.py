import os
import re
import sys
import urllib.request
from bs4 import BeautifulSoup
from download_and_upload import fetch_playlist_items

if __name__ == '__main__':
    items = fetch_playlist_items()
    print(f"Total lectures found: {len(items)}\n")
    for item in items[:15]:
        print(f"Week {item['week_num']:02d} [{item['week_folder']}] -> File: '{item['filename']}'")
