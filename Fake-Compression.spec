# PyInstaller build specification for the Windows desktop application.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
src = root / "src"
icon = src / "fake_compression" / "assets" / "fake-compression.svg"

a = Analysis(
    ["main.py"],
    pathex=[str(src)],
    binaries=[],
    datas=[(str(icon), "fake_compression/assets")],
    hiddenimports=collect_submodules("shiboken6"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "jupyter", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Fake-Compression",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
