# Fake-Compression

A Windows desktop utility for creating encrypted, split 7-Zip archives and restoring them from a password-protected `.fc` manifest.

## Design direction

A practical desktop tool, not a dashboard template: restrained warm-neutral surfaces, compact typography, plain navigation, clear file paths and task output. No gratuitous gradients, decorative statistics or oversized icon cards.

## Features in 0.1

- PySide6 desktop interface with packaging, extraction and settings pages.
- Automatic split policy: up to 1 GiB = single archive; above 1 GiB through 5 GiB = 2 GiB volumes; above 5 GiB = 3 GiB volumes.
- 7-Zip AES-256 archive encryption with encrypted headers (`-mhe=on`).
- Password-protected `.fc` manifest using scrypt and AES-256-GCM.
- SHA-256 validation of all archive volumes before extraction.
- Optional video association as a separate preview file. Video bytes are never modified or used to conceal data.

## Requirements

- Python 3.10+
- Windows 10/11
- 7-Zip command-line executable (`7z.exe`)
- Dependencies from `requirements.txt`

## Run from source

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
py main.py
```

7-Zip is detected from PATH and common installation folders. You can override its path in the Settings page.

## Tests

```powershell
py -m pip install pytest
$env:PYTHONPATH = "src"
py -m pytest
```

## Important

Keep the `.fc` manifest and every archive volume together. The master password cannot be recovered if lost. This is an initial development build; test with disposable copies before trusting important data. The first version is not yet hardened against every malicious archive extraction scenario. Do not run extraction as administrator.
