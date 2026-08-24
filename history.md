# History

## 2026-08-24T15:17:00+05:30 - Accurate File Numbering & Public GitHub Setup
- **User Request**: Fix inaccurate file numbering, correct weekly folder organization, start download, make GitHub repository public, and provide single-line copy-paste command for Cloud Shell.
- **Problem**: Files were missing zero-padded prefix numbers (e.g. `01 - Lecture 1 - ...`) causing unsorted playlist listing. `config.ini` missing for user-configured storage directories.
- **Fix & Implementation**:
  1. Updated `download_and_upload.py` and `downloader.py` to format filenames with accurate zero-padded indices (`01` to `75`).
  2. Added `config.ini` support for base storage directory, upload flags, and week processing order.
  3. Initialized git repository, committed all files, and published public repository to GitHub (`skc-coder/nptel-downloader`).
  4. Launched the download process in the background.
