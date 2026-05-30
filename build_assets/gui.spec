# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Basketball Inability Analyzer macOS app."""

import sys
from pathlib import Path

_root = Path(SPECPATH).parent  # project root (parent of build_assets/)
_app_name = "Basketball Analyzer"

a = Analysis(
    [str(_root / 'src/gui.py')],
    pathex=[str(_root)],
    binaries=[],
    datas=[
        (str(_root / 'data'), 'data'),
    ],
    hiddenimports=['src.models', 'src.analyzer', 'src.calculator', 'src.benchmarks'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'email',
        'http',
        'xml',
        'pydoc',
        'distutils',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=_app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_root / 'build_assets/icons/icon.icns'),
)

app = BUNDLE(
    exe,
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
