# FCKey Reader

A small standalone graphical utility for reading Fake-Compression `.fckey` files.

## What it does

1. Select a `.fckey` file.
2. Enter the original first-layer and second-layer passwords used when creating the package.
3. Authenticate and decrypt the metadata.
4. Show the source folder, archive formats, volume count and inventory count.
5. Derive the exact printable passwords expected by standard 7-Zip and WinRAR, with show/hide and copy controls.

It does not create archives, extract files, or require 7-Zip / WinRAR to be installed.

## Build on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-fcreader.txt
pyinstaller --clean --noconfirm fcreader.spec
```

The executable is created at `dist\FCKey-Reader.exe`.

## Compatibility

The decoder intentionally mirrors the FCKEY v1 format in Fake-Compression: AES-256-GCM, scrypt (N=32768, r=8, p=1), the same authenticated-data marker and the same layer-specific external-password derivation. Keep the two implementations in sync when the format version changes.
