# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
icon = root / "build" / "fake-compression.ico"
svg = root / "src" / "fake_compression" / "assets" / "fake-compression.svg"

a = Analysis(
    ["fcreader.py"],
    pathex=["."],
    binaries=[],
    datas=[(str(svg), "fake_compression/assets")],
    hiddenimports=collect_submodules("cryptography"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="FCKey-Reader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon),
)
