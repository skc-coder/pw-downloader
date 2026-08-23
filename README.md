# NPTEL Modern C++ Video Downloader & Google Drive Uploader

Automated tool to download NPTEL Modern C++ video course, rename to standardized formats (`L<N>-title` / `T<N>-title`), categorize into week folders, and upload to Google Drive using `rclone`.

## Order of Execution
Processes Week 3 to Week 12 first, followed by Week 1 to Week 2 as requested.

## Setup & Installation
```bash
git clone <repo-url>
cd "nptel downloader"
uv venv
source .venv/bin/activate
uv pip install yt-dlp beautifulsoup4
```

## Running the Code
```bash
python download_and_upload.py
```

## Update & Run
```bash
git pull && python download_and_upload.py
```
