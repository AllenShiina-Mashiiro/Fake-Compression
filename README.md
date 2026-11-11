# 📦 Fake-Compression

A Windows desktop utility for creating encrypted archives and restoring
original folders.

[简体中文](README.zh.md) | [English](README.md)

## 🎨 Design Direction

This is a practical desktop utility, not a dashboard template.

-   🎨 A restrained, warm neutral color palette
-   🔤 Clean typography and clear navigation
-   📁 Clearly displayed file paths and task output
-   🚫 No unnecessary gradients, decorative statistics, or oversized
    icon cards

## 🚧 Current Version: `1.1.4-Alpha`

This version is in the completion stage. For subsequent updates, please
follow the [Beta
branch](https://github.com/AllenShiina-Mashiiro/Fake-Compression/tree/Beta).

### ✨ Core Features

-   🖥️ A PySide6 desktop interface for packaging and restoration.
-   🔐 The archive engine is being migrated to a dual-layer encryption
    format:
    -   Layer 1: 7-Zip AES-256
    -   Layer 2: WinRAR RAR5 AES-256
-   📂 Volume-splitting strategy:
    -   Less than 1 GiB: a single archive
    -   1 GiB to 5 GiB: 2 GiB volumes
    -   More than 5 GiB: 4 GiB volumes
-   👁️ Password visibility control.
-   🛡️ scrypt uses explicit, bounded OpenSSL memory allocation to avoid
    failures caused by the common 32 MiB default limit.
-   🔎 SHA-256 verification of archive volumes and original files during
    restoration.
-   📊 Parses actual progress from 7-Zip console output.
-   ⏹️ Background tasks can be cancelled.
-   ⚙️ Uses Windows user settings to persist:
    -   The 7-Zip executable path
    -   The output folder
    -   Window geometry
-   🔒 Extraction path validation rejects:
    -   Path traversal
    -   Absolute paths
    -   Duplicate case-insensitive names
    -   Windows device names
    -   Symbolic links and hard links
-   📁 Extraction takes place in a temporary staging directory. Existing
    destination items are never silently overwritten.
-   📦 Both the service layer and desktop interface support batch
    packaging and batch restoration. Each item is processed
    independently; a failure in one item does not stop the remaining
    batch.

## 🧠 How It Works

-   🧾 The current version of Fake-Compression creates three archive
    stages: \> 1. Encrypted 7-Zip volumes \> 2. An encrypted WinRAR RAR5
    archive \> 3. A regular ZIP container containing only the archive
    file

-   🔑 Authenticated metadata is stored in an external `.fckey` sidecar
    file whose name matches the final package.

-   🗂️ Target Archive Layout (1.1.4-Alpha)

The target workflow uses dual-layer encrypted archives and external
metadata verification.

### 🔐 Archive Structure

> 1.  Create AES-256 encrypted 7-Zip volumes using the first-layer
>     password.
> 2.  Place all volumes in a directory named after the source folder.
> 3.  Use WinRAR RAR5 AES-256 to encrypt the entire directory into a
>     single, non-split RAR archive, using the second-layer password.
> 4.  Place only the encrypted RAR file (`payload.rar`) inside a
>     regular, unencrypted ZIP file.
> 5.  Store authenticated metadata in an external `.fckey` sidecar file
>     with the same name as the final package. Do not copy the metadata
>     into the ZIP file.
> 6.  Give the ZIP file a `.rar` extension.

> ⚠️ The third layer has no password. Archive tools that inspect file
> signatures can identify the actual format and open it as a ZIP file.
> The internal `payload.rar` remains protected by the second-layer
> password.

### 🔄 Restoration Process

Fake-Compression performs the following operations:

-   📖 Reads the adjacent `.fckey` sidecar file.
-   🔓 Decrypts and verifies the metadata.
-   📦 Extracts the encrypted archive from the outer ZIP container.
-   🔐 Restores the two encrypted archive layers.
-   🔎 Verifies the original file manifest.
-   📏 Verifies file sizes.
-   🔏 Verifies the SHA-256 hashes of all original files.

If you receive a disguised `.mp4` file and its `.fckey` file created by
`Fake-Compression`, you can still extract the contents manually:

> -   1.  Change the `.mp4` extension to `.zip` or `.rar`.
> -   2.  Use the `Fake-Compression-fcreader.exe` extractor to retrieve
>         the **two-layer special keys** inside.
> -   3.  Use `WinRAR` with the `second-layer key` to extract the `.zip`
>         file. After extraction, you will obtain the first-layer
>         volumes.
> -   4.  Then use `7-Zip` with the `first-layer key` to extract the
>         final contents and recover the source files.

⚠️ **The `Fake-Compression-fcreader` extractor is currently available in
the [fcreader
branch](https://github.com/AllenShiina-Mashiiro/Fake-Compression/tree/fcreader).**

## 📝 File Naming and Compatibility

-   The external package filename is not used as an identifier.
-   The external package can be renamed freely, provided that its
    corresponding `.fckey` sidecar file is renamed to match.
-   During restoration, the original folder name and archive layout are
    read from authenticated metadata.
-   Internal paths must never be inferred from the external filename.
-   New packages contain only the fixed `payload.rar` entry.
-   Older packages containing the `metadata.fckey` entry remain
    readable.

## 🛠️ Packaging and Releases

Automatic generation of EXE files, portable ZIP packages, and installers
has been disabled. Maintainers will manually package release versions
after source-code verification.

Please visit `Releases` to download the version assets you need.

Currently supported: Windows 10/11 (x64).

Required external tools:

-   7-Zip
-   WinRAR

These remain external dependencies required by the project and are not
bundled with the application.

## 📋 Prerequisites / Required Environment

  Item                     Requirement
  ------------------------ -----------------------------------
  🐍 Python                3.10+
  💻 Operating System      Windows 10 / 11
  🗜️ 7-Zip                 Command-line executable `7z.exe`
  🔐 WinRAR                Command-line executable `rar.exe`
  📦 Python Dependencies   `requirements.txt`

Windows 10/11 provides the intended full desktop experience.

## 🚀 Run from Source

### 1. Clone the Repository

``` powershell
git clone <repository-url>
cd Fake-Compression
```

### 2. Create a Virtual Environment

``` powershell
py -m venv .venv
```

### 3. Activate the Virtual Environment

``` powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

``` powershell
py -m pip install -r requirements.txt
```

### 5. Configure the Python Module Path

``` powershell
$env:PYTHONPATH = "src"
```

### 6. Launch the Application

``` powershell
py main.py
```

### ⚙️ External Tool Detection

7-Zip and WinRAR are detected from:

-   The Windows `PATH` environment variable
-   Common installation directories

The executable paths for both programs can also be configured manually
in the application settings.

## 🧪 Testing

### 1. Install Test Dependencies

``` powershell
py -m pip install pytest
```

### 2. Configure the Module Path

``` powershell
$env:PYTHONPATH = "src"
```

### 3. Run Tests

``` powershell
py -m pytest -q
```

### 🔬 Windows End-to-End Testing

Full end-to-end verification requires a Windows system with both 7-Zip
and WinRAR installed.

CI and unit tests alone cannot determine compatibility with the versions
of the compression tools installed on a system.

The project provides a real-tool regression test:

``` text
tests/test_archive_e2e.py
```

This test runs automatically when both external executables are
detected.

The main verification points include:

-   📦 A plain ZIP container with a `.rar` extension
-   🗂️ Multi-volume archive extraction
-   📁 RAR directory layout
-   📝 Arbitrary output-file renaming
-   🔎 SHA-256 integrity verification using disposable test data

## 🧩 Standalone Utility

A standalone graphical `.fckey` reader is being developed on the
separate `fcreader` branch.

It is intentionally not bundled with the main Fake-Compression
application.

## 🛡️ Security Notes

> ⚠️ **Important: The current project prototype has not yet been
> hardened to the level of a high-security vault.**

-   The `.fckey` binary extension itself provides no security.
-   Confidentiality and tamper detection must rely on authenticated
    encryption.
-   Never store original passwords in plaintext.
-   The command-line interfaces of 7-Zip and WinRAR may expose password
    arguments to local process inspection while a task is running.
-   Always test with disposable copies before trusting important data.
-   Do not run the extraction program as an administrator.

## 🌿 Branch and Release Strategy

The project uses a dual-branch Beta / Alpha development and release
strategy.

### 🧪 Beta --- Development and Validation Branch

-   The active development branch.
-   New features and fixes are committed here first.
-   Used for feature testing, compatibility validation, and bug fixing.
-   Not intended to be released directly to end users.

### 🚀 Alpha --- User-Facing Release Branch

-   Once Beta validation is complete, tested commits are promoted to
    Alpha.
-   Serves as the validated release version for users.
-   Only commits that have completed testing are accepted.

> 🔴 **Release Rule: Never publish an untested Beta version.**
