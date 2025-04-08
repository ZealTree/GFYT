from datetime import datetime

# Генерируем версию на основе текущей даты и времени
build_time = datetime.now().strftime("%y%m%d_%H%M%S")  # Формат YYMMDD_HHMMSS
yy = int(build_time[0:2])  # Год
mm = int(build_time[2:4])  # Месяц
dd = int(build_time[4:6])  # День
hhmmss = int(build_time[7:])  # Часы, минуты, секунды как одно число

# Формируем версию как кортеж для PyInstaller
version_tuple = f"({yy}, {mm}, {dd}, {hhmmss})"

# Шаблон version_info.txt
version_info = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'xAI'),
        StringStruct(u'FileDescription', u'yt-dlp GUI'),
        StringStruct(u'FileVersion', u'{build_time}'),
        StringStruct(u'InternalName', u'yt-dlp_gui'),
        StringStruct(u'LegalCopyright', u'© 2025 xAI. All rights reserved.'),
        StringStruct(u'OriginalFilename', u'yt-dlp_gui_{build_time}.exe'),
        StringStruct(u'ProductName', u'yt-dlp GUI'),
        StringStruct(u'ProductVersion', u'{build_time}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

# Записываем в файл
with open("version_info.txt", "w", encoding="utf-8") as f:
    f.write(version_info)

print(f"Generated version_info.txt with version {build_time}")