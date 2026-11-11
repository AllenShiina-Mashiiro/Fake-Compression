# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH)
ICON_PATH = ROOT / "src" / "fake_compression" / "assets" / "fake-compression.ico"
SVG_PATH = ROOT / "src" / "fake_compression" / "assets" / "fake-compression.svg"

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT / 'src')],
    binaries=[],
    datas=[
        (str(ICON_PATH), 'assets'),
        (str(SVG_PATH), 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Fake-Compression',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH),
)