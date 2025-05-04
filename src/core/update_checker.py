from PyQt6.QtCore import QThread, pyqtSignal
import requests
from .config import ConfigManager

class UpdateChecker(QThread):
    finished = pyqtSignal(bool, str, str)

    def run(self):
        try:
            headers = {"User-Agent": ConfigManager.USER_AGENT}
            response = requests.get(ConfigManager.YTDLP_RELEASES_URL, headers=headers)
            response.raise_for_status()

            release_info = response.json()
            latest_version = release_info['tag_name']
            self.finished.emit(True, "Проверка завершена", latest_version)
        except Exception as e:
            self.finished.emit(False, f"Ошибка проверки обновлений: {str(e)}", "")