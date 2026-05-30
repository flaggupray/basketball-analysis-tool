# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — onedir mode for fast macOS .app launch."""

import sys
from pathlib import Path

_root = Path(SPECPATH).parent
_app_name = "Basketball Analyzer"

a = Analysis(
    [str(_root / 'src/gui.py')],
    pathex=[str(_root)],
    binaries=[],
    datas=[(str(_root / 'data'), 'data')],
    hiddenimports=[
        'src.models', 'src.analyzer', 'src.calculator', 'src.benchmarks',
        'src.camera', 'src.video_analyzer', 'src.ai_analyzer', 'src.config',
        'cv2', 'numpy', 'PIL', 'PIL.Image', 'PIL.ImageTk',
        'cv2.videoio_registry',
        'cryptography', 'cryptography.fernet',
        'requests', 'urllib3',
    ],
    excludes=['tkinter.test', 'unittest', 'pydoc', 'distutils', 'setuptools'],
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=_app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(_root / 'build_assets/icons/icon.icns'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=_app_name,
)

app = BUNDLE(
    coll,
    name=f"{_app_name}.app",
    icon=str(_root / 'build_assets/icons/icon.icns'),
    bundle_identifier='com.basketball.analyzer',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '11.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleName': _app_name,
        'CFBundleDisplayName': 'Basketball Analyzer',
        'NSHumanReadableCopyright': 'MIT License',
    },
)
