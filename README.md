# Fake-Compression

A Windows desktop utility for creating encrypted archives and restoring original folders.

## Design direction

A practical desktop tool, not a dashboard template: restrained warm-neutral surfaces, compact typography, plain navigation, clear file paths and task output. No gratuitous gradients, decorative statistics or oversized icon cards.

## Current development build: 1.0.1-beta

This version is an active development build. Do not treat the full dual-layer packaging workflow as complete until the end-to-end Windows tests have passed.

- PySide6 desktop interface for packaging, restoration and settings.
- Existing archive engine currently creates a password-protected 7-Zip AES-256 archive and encrypted integrity manifest.
- Automatic split policy: up to 1 GiB = single archive; above 1 GiB through 5 GiB = 2 GiB volumes; above 5 GiB = 3 GiB volumes.
- Password visibility controls and an About menu with project/developer GitHub links.
- scrypt uses an explicit bounded OpenSSL memory allowance to avoid the common 32 MiB default-cap failure.
- SHA-256 validation of archive volumes and original files during restoration.
- Real progress parsing from 7-Zip console output and cancellable background tasks.
- Persistent 7-Zip path, output folders and window geometry using Windows user settings.
- Extraction path validation rejects traversal, absolute paths, duplicate case-insensitive names, Windows device names and symbolic/hard links.
- Extraction occurs in a temporary staging folder; existing destination items are never silently overwritten.
- `.fckey` binary authenticated metadata and video-payload prototype modules exist, but are not yet wired into the end-to-end UI workflow.

## Target archive layout (1.0.1-beta development)

1. Create AES-256 7-Zip volumes using layer-one password.
2. Put every volume into one directory named after the source folder.
3. Use WinRAR RAR5 AES-256 to encrypt that entire directory as one non-split RAR archive using layer-two password.
4. Place the encrypted `.fckey` metadata and RAR archive into a normal outer package.
5. Optionally wrap the outer package in the supported video-payload container.
6. Restore in reverse order and verify the original file inventory, sizes and SHA-256 hashes.

The outer package filename is not an identity field. It may be renamed; restoration must locate fixed internal entries and read the original folder name and archive layout from authenticated `.fckey` metadata. The implementation must never infer internal paths from the outer filename.

## Requirements

- Python 3.10+
- Windows 10/11 for the intended desktop experience
- 7-Zip command-line executable (`7z.exe`)
- WinRAR command-line executable (`rar.exe`) for the target dual-layer workflow
- Dependencies from `requirements.txt`

## Run from source

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
py main.py
```

7-Zip is detected from PATH and common installation folders. The WinRAR executable will be configurable in Settings as the second-layer workflow is integrated.

## Tests

```powershell
py -m pip install pytest
$env:PYTHONPATH = "src"
py -m pytest -q
```

The required end-to-end validation environment is Windows with both 7-Zip and WinRAR installed. CI/unit tests alone cannot establish compatibility with the installed archiver versions.

## Security notes

The `.fckey` binary extension is not security by itself. Confidentiality and tamper detection must come from authenticated encryption; never store original passwords in plaintext. 7-Zip and WinRAR command-line interfaces may expose password arguments to local process inspection while a task is running. This prototype is not yet a hardened high-assurance vault. Test with disposable copies before trusting important data, and do not run extraction as administrator.

## Branch and release policy

- `Beta` is the active development and validation branch. New features and fixes land here first.
- After Beta validation is complete, promote the tested commit to `Alpha` for the user-facing release line.
- Never promote an untested Beta commit.
