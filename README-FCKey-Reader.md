# FCKey Reader

A small, independent Windows utility for reading Fake-Compression .fckey metadata.

## What it does
1. Open a .fckey file from the app or by double-clicking it after installation.
2. Enter the original first-layer and second-layer passwords used when creating the package.
3. Authenticate and decrypt the metadata.
4. Show the source folder, archive formats, volume count and inventory count.
5. Derive the exact printable passwords expected by standard 7-Zip and WinRAR, with show/hide and copy controls.

It does not create archives, extract files, or require 7-Zip / WinRAR to be installed.

## Windows distributions
When packaging locally, you can create these artifacts:
- FCKey-Reader.exe — standalone executable.
- FCKey-Reader-Portable.zip — portable copy; no file association is registered.
- FCKey-Reader-Setup.exe — installer that registers .fckey double-click opening and removes the association when uninstalled.

The installer creates Start Menu shortcuts and offers an optional desktop shortcut. The portable build can be run directly; to open a file, pass its path as the first argument.

## Build on Windows
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-fcreader.txt
py -m pip install pyinstaller
pyinstaller --clean --noconfirm fcreader.spec
choco install innosetup --no-progress -y
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" FCKey-Reader.iss
```

The executable is created at dist\FCKey-Reader.exe; the installer is dist\FCKey-Reader-Setup.exe.

The Reader repository contains only the Reader application, its independent FCKEY v1 decoder, its own tests and packaging files. It does not vendor or import the Fake-Compression application source. The decoder protocol is documented below; when the FCKEY format changes, update the Reader implementation and its compatibility tests deliberately.

## Compatibility
The decoder intentionally mirrors FCKEY v1: AES-256-GCM, scrypt (N=32768, r=8, p=1), the same authenticated-data marker and the same layer-specific external-password derivation. Keep both implementations in sync when the format version changes.

## Source entry point
Run `python main.py` to launch the standalone Reader. This branch's `main.py` intentionally imports `fcreader.main`; it does not launch the Fake-Compression archive application.
