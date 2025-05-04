from PyQt6.QtCore import QThread, pyqtSignal
import requests
import subprocess
from .config import ConfigManager

class DownloaderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, destination):
        super().__init__()
        self.url = url
        self.destination = destination
        self._is_running = True

    def run(self):
        try:
            headers = {"User-Agent": ConfigManager.USER_AGENT}
            response = requests.get(self.url, headers=headers, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self._is_running:
                        raise Exception("Загрузка отменена пользователем")
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
                        self.progress.emit(progress)

            file_size = os.path.getsize(self.destination) / (1024 * 1024)
            ConfigManager.log_download(f"Скачан файл {self.destination}, размер: {file_size:.2f} MB")

            self.finished.emit(True, "Файл успешно загружен")
        except Exception as e:
            self.finished.emit(False, f"Ошибка загрузки: {str(e)}")

    def stop(self):
        self._is_running = False

class DownloadThread(QThread):
    output_received = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self._is_running = True
        self.process = None
        self.log_buffer = []
        self.buffer_lock = False

    def run(self):
        try:
            cmd = [ConfigManager.get_ytdlp_path(), "--config-location", ConfigManager.CONFIG_FILE, self.url]
            ConfigManager.log_download(f"Запуск команды: {' '.join(cmd)}")

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            while self._is_running:
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    self.add_to_buffer(output.strip())

            return_code = self.process.wait()
            success = return_code == 0
            msg = "Загрузка завершена успешно!" if success else f"Ошибка (код {return_code})"
            self.finished.emit(success, msg)
            ConfigManager.log_download(self.url, success)

        except Exception as e:
            self.add_to_buffer(f"Исключение: {str(e)}")
            self.finished.emit(False, f"Исключение: {str(e)}")
            ConfigManager.log_download(self.url, False)

    def add_to_buffer(self, message):
        while self.buffer_lock:
            QThread.msleep(10)
        self.buffer_lock = True
        self.log_buffer.append(message)
        self.buffer_lock = False
        self.output_received.emit("")

    def stop(self):
        self._is_running = False
        if self.process:
            self.process.terminate()