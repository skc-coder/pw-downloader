# NPTEL Modern C++ Downloader & Uploader

A resumable, automated pipeline for downloading Digimat NPTEL Modern C++ course lectures with zero-padded file numbering, volume boosting (ffmpeg +6dB / 2.0x), weekly folder organization, and rclone Google Drive auto-syncing.

## Setup & Installation

```bash
git clone https://github.com/skc-coder/nptel-downloader.git
cd nptel-downloader
python3 -m venv venv
source venv/bin/activate
pip install beautifulsoup4
```

## Configuration

Edit `config.ini` to set local paths, Google Drive targets, and week download order:

```ini
[GENERAL]
base_storage_dir = /mnt/storage/nptel_downloads
gdrive_remote_root = gdrive:NPTEL Modern C++
upload_to_gdrive = true

[PIPELINE]
week_order = 3,4,5,6,7,8,9,10,11,12,1,2
```

## Running the Code

```bash
python3 download_and_upload.py
```

## Cloud Shell Quick Run Command

Run this single command on Google Cloud Shell to clone, setup, and start downloading:

```bash
git clone https://github.com/skc-coder/nptel-downloader.git && cd nptel-downloader && python3 -m venv venv && source venv/bin/activate && pip install beautifulsoup4 && python3 download_and_upload.py
```

## Update & Run

```bash
git pull && python3 download_and_upload.py
```
