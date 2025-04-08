import os
import subprocess
from datetime import datetime

# Генерируем версию
build_time = datetime.now().strftime("%y%m%d_%H%M%S")

# Генерируем version_info.txt
subprocess.run(["python", "generate_version.py"])

# Запускаем сборку
subprocess.run(["pyinstaller", "build.spec"])

print(f"Сборка завершена: yt-dlp_gui_{build_time}.exe")