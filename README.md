# Fake-Compression

A Windows desktop utility for creating encrypted, split 7-Zip archives and restoring them from a password-protected `.fc` manifest.

## Design direction

A practical desktop tool, not a dashboard template: restrained warm-neutral surfaces, compact typography, plain navigation, clear file paths and task output. No gratuitous gradients, decorative statistics or oversized icon cards.

## Current development build: 1.0.0-beta.1

- PySide6 desktop interface for packaging, restoration and settings.
- Automatic split policy: up to 1 GiB = single archive; above 1 GiB through 5 GiB = 2 GiB volumes; above 5 GiB = 3 GiB volumes.
- 7-Zip AES-256 archive encryption with encrypted headers (`-mhe=on`); passwords are user-selected and confirmed in the UI.
- Password visibility controls and an About menu with project/developer GitHub links.
- scrypt uses an explicit bounded OpenSSL memory allowance to avoid the common 32 MiB default-cap failure.
- Password-protected `.fc` manifest using scrypt and AES-256-GCM.
- SHA-256 validation of every archive volume before extraction.
- Real progress parsing from 7-Zip console output and cancellable background tasks.
- Persistent 7-Zip path, output folders and window geometry using Windows user settings.
- Extraction path validation rejects traversal, absolute paths, duplicate case-insensitive names, Windows device names and symbolic/hard links.
- Package names are checked against Windows filename restrictions; existing package outputs are never silently overwritten.
- Extraction occurs in a temporary staging folder; existing destination items are never silently overwritten.
- Optional video association as a separate preview file. Video bytes are never modified or used to conceal data.
- GitHub Actions test workflow targets Windows and Ubuntu.

## Requirements

- Python 3.10+
- Windows 10/11 for the intended desktop experience
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

7-Zip is detected from PATH and common installation folders. You can override its path in Settings; the path and output folders are saved in the current Windows user profile.

## Tests

```powershell
py -m pip install pytest
$env:PYTHONPATH = "src"
py -m pytest -q
```

## Security notes

Keep the `.fc` manifest and every archive volume together. The master password cannot be recovered if lost. The video is a separate preview file and is not a steganographic container.

7-Zip's command-line interface receives the derived archive password as a process argument. Other local processes with sufficient permissions may be able to inspect process arguments while a task is running. This prototype is not yet a hardened high-assurance vault. Test with disposable copies before trusting important data, and do not run extraction as administrator.


## Branch and release policy

- `Beta` is the active development and validation branch. New features and fixes land here first.
- After Beta validation is complete, promote the tested commit to `Alpha` for the user-facing release line.
- Branch names are `Beta` and `Alpha`; package versions use matching prerelease labels, for example `1.0.0-beta.1` and `1.0.0-alpha.1`.
- Keep release tags on the exact commit that was validated. Never promote an untested Beta commit.
