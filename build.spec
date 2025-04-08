# -*- mode: python ; coding: utf-8 -*-

from datetime import datetime
import os

# Генерируем версию и имя файла на основе текущей даты и времени
build_time = datetime.now().strftime("%y%m%d_%H%M%S")  # Формат YYMMDD_HHMMSS
output_name = f"yt-dlp_gui_{build_time}"  # Имя выходного файла

block_cipher = None

a = Analysis(
    ['gui_yt-dlp.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=output_name,
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
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version='version_info.txt',  # Указываем файл с версией
)

# Убираем COLLECT, если нужна однофайловая сборка
# Если нужна сборка с папкой, раскомментируйте:
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name=output_name,
# )