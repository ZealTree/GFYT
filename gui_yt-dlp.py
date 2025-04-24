import os
import sys
import subprocess
import requests
import re
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QTextEdit, QFileDialog, QMessageBox, QProgressDialog,
    QRadioButton, QDialog, QTableWidget, QTableWidgetItem,
    QDialogButtonBox, QHeaderView, QStatusBar, QGroupBox, QFormLayout, QButtonGroup
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QUrl, QTimer
from PyQt6.QtGui import QDesktopServices, QIcon, QGuiApplication, QAction

# Константы
YTDLP_RELEASES_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
USER_AGENT = "yt-dlp-gui/1.0"
SUPPORTED_BROWSERS = ["brave", "chrome", "firefox", "vivaldi"]

def get_version():
    try:
        with open("version.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0"  # Fallback version

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
            headers = {"User-Agent": USER_AGENT}
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

            self.finished.emit(True, "Файл успешно загружен")
        except Exception as e:
            self.finished.emit(False, f"Ошибка загрузки: {str(e)}")

    def stop(self):
        self._is_running = False

class ConfigManager:
    CONFIG_FILE = "yt-dlp.conf"
    LOG_FILE = "yt-dlp-gui.log"

    DEFAULT_CONFIG = """# yt-dlp Configuration File
--output "%(title)s.%(ext)s"
--paths "{}/Videos"
--merge-output-format mp4
--no-overwrites
""".format(str(Path.home()))

    @classmethod
    def init_config(cls):
        if not os.path.exists(cls.CONFIG_FILE):
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(cls.DEFAULT_CONFIG)

        if not os.path.exists(cls.LOG_FILE):
            with open(cls.LOG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"YT-DLP GUI Log - Created {datetime.now()}\n")

    @classmethod
    def save_config(cls, config_text):
        try:
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(config_text)
            return True
        except Exception as e:
            print(f"Config save error: {e}")
            return False

    @classmethod
    def load_config(cls):
        try:
            with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Config load error: {e}")
            return None

    @classmethod
    def parse_config(cls, config_text):
        params = {
            'output': '%(title)s.%(ext)s',
            'paths': str(Path.home() / "Videos"),
            'merge_format': 'mp4',
            'proxy': None,
            'cookies': None,
            'cookies_from_browser': None,
            'no_overwrites': False,
            'sponsorblock_remove': False,
            'add_metadata': False,
            'embed_thumbnail': False
        }

        lines = [line.strip() for line in config_text.split('\n') if line.strip() and not line.strip().startswith('#')]

        for line in lines:
            if line.startswith('--output'):
                params['output'] = line.split('"')[1]
            elif line.startswith('--paths'):
                params['paths'] = line.split('"')[1]
            elif line.startswith('--merge-output-format'):
                params['merge_format'] = line.split()[-1]
            elif line.startswith('--proxy'):
                params['proxy'] = line.split()[-1]
            elif line.startswith('--cookies'):
                params['cookies'] = line.split('"')[1]
            elif line.startswith('--cookies-from-browser'):
                params['cookies_from_browser'] = ' '.join(line.split()[1:])
            elif line == '--no-overwrites':
                params['no_overwrites'] = True
            elif line == '--sponsorblock-remove all':
                params['sponsorblock_remove'] = True
            elif line == '--add-metadata':
                params['add_metadata'] = True
            elif line == '--embed-thumbnail':
                params['embed_thumbnail'] = True

        return params

    @classmethod
    def log_download(cls, url, success=True):
        with open(cls.LOG_FILE, 'a', encoding='utf-8') as f:
            status = "SUCCESS" if success else "FAILED"
            f.write(f"[{datetime.now()}] {status} - {url}\n")

    @classmethod
    def get_ytdlp_path(cls):
        if os.name == 'nt':
            return "yt-dlp.exe"
        return "./yt-dlp"

    @classmethod
    def check_ytdlp_exists(cls):
        return os.path.exists(cls.get_ytdlp_path())

    @classmethod
    def get_ytdlp_version(cls):
        if not cls.check_ytdlp_exists():
            return None

        try:
            result = subprocess.run(
                [cls.get_ytdlp_path(), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.stdout.strip()
        except Exception:
            return None

class UpdateChecker(QThread):
    finished = pyqtSignal(bool, str, str)

    def run(self):
        try:
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(YTDLP_RELEASES_URL, headers=headers)
            response.raise_for_status()

            release_info = response.json()
            latest_version = release_info['tag_name']
            self.finished.emit(True, "Проверка завершена", latest_version)
        except Exception as e:
            self.finished.emit(False, f"Ошибка проверки обновлений: {str(e)}", "")

class TemplateEditorDialog(QDialog):
    def __init__(self, current_template, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Конструктор шаблонов")
        self.setMinimumSize(500, 400)
        self.current_template = current_template
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.template_edit = QLineEdit(self.current_template)
        self.template_edit.setPlaceholderText("Введите шаблон или используйте конструктор ниже")
        layout.addWidget(QLabel("Шаблон имени файла:"))
        layout.addWidget(self.template_edit)

        self.setup_variables_table()
        layout.addWidget(QLabel("Доступные переменные:"))
        layout.addWidget(self.variables_table)

        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.update_preview()
        layout.addWidget(QLabel("Пример:"))
        layout.addWidget(self.preview_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.template_edit.textChanged.connect(self.update_preview)

    def setup_variables_table(self):
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(3)
        self.variables_table.setHorizontalHeaderLabels(["Переменная", "Описание", "Действие"])
        self.variables_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.variables_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.variables_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.variables_table.setRowCount(8)

        variables = [
            ("%(title)s", "Название видео", "Вставить"),
            ("%(uploader)s", "Автор канала", "Вставить"),
            ("%(upload_date)s", "Дата загрузки (YYYYMMDD)", "Вставить"),
            ("%(id)s", "ID видео", "Вставить"),
            ("%(ext)s", "Расширение файла", "Вставить"),
            ("%(playlist_title)s", "Название плейлиста", "Вставить"),
            ("%(playlist_index)s", "Номер в плейлиста", "Вставить"),
            ("%(height)s", "Высота видео в пикселях", "Вставить")
        ]

        for row, (var, desc, action) in enumerate(variables):
            self.variables_table.setItem(row, 0, QTableWidgetItem(var))
            self.variables_table.setItem(row, 1, QTableWidgetItem(desc))

            btn = QPushButton(action)
            btn.clicked.connect(lambda _, v=var: self.insert_variable(v))
            self.variables_table.setCellWidget(row, 2, btn)

    def insert_variable(self, variable):
        current = self.template_edit.text()
        cursor_pos = self.template_edit.cursorPosition()
        self.template_edit.setText(current[:cursor_pos] + variable + current[cursor_pos:])
        self.template_edit.setFocus()

    def update_preview(self):
        template = self.template_edit.text()
        example = template
        example = example.replace("%(title)s", "Пример видео")
        example = example.replace("%(uploader)s", "Автор")
        example = example.replace("%(upload_date)s", "20230101")
        example = example.replace("%(id)s", "dQw4w9WgXcQ")
        example = example.replace("%(ext)s", "mp4")
        example = example.replace("%(playlist_title)s", "Мой плейлист")
        example = example.replace("%(playlist_index)s", "001")
        example = example.replace("%(height)s", "1080")

        self.preview_label.setText(f"<b>{example}</b>")

    def get_template(self):
        return self.template_edit.text()

class OutputSettingsDialog(QDialog):
    """Диалоговое окно для настроек вывода."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки вывода")
        self.setMinimumSize(400, 200)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(self.parent.path_input.text())
        self.path_input.setToolTip("Путь для сохранения загруженных файлов")
        self.path_browse_btn = QPushButton("Обзор...")
        self.path_browse_btn.setToolTip("Выбрать папку для сохранения")
        self.path_browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.path_browse_btn)
        layout.addWidget(QLabel("Путь сохранения:"))
        layout.addLayout(path_layout)

        template_layout = QHBoxLayout()
        self.template_input = QLineEdit(self.parent.template_input.text())
        self.template_input.setToolTip("Шаблон имени выходного файла")
        self.template_btn = QPushButton("Конструктор...")
        self.template_btn.setToolTip("Открыть конструктор шаблонов")
        self.template_btn.clicked.connect(self.edit_template)
        template_layout.addWidget(self.template_input)
        template_layout.addWidget(self.template_btn)
        layout.addWidget(QLabel("Шаблон имени файла:"))
        layout.addLayout(template_layout)

        self.merge_combo = QComboBox()
        self.merge_combo.addItems(["mp4", "mkv"])
        self.merge_combo.setCurrentText(self.parent.merge_combo.currentText())
        self.merge_combo.setToolTip("Формат для объединения видео и аудио")
        layout.addWidget(QLabel("Формат объединения:"))
        layout.addWidget(self.merge_combo)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения", self.path_input.text())
        if path:
            if os.access(path, os.W_OK):
                self.path_input.setText(path)
            else:
                QMessageBox.warning(self, "Ошибка", "Нет прав на запись в выбранную папку")

    def edit_template(self):
        dialog = TemplateEditorDialog(self.template_input.text(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.template_input.setText(dialog.get_template())

    def save(self):
        self.parent.path_input.setText(self.path_input.text())
        self.parent.template_input.setText(self.template_input.text())
        self.parent.merge_combo.setCurrentText(self.merge_combo.currentText())

    def on_accept(self):
        self.save()
        self.accept()

class ProxySettingsDialog(QDialog):
    """Диалоговое окно для настроек прокси."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки прокси")
        self.setMinimumSize(300, 200)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.proxy_none_rb = QRadioButton("Не использовать прокси")
        self.proxy_none_rb.setToolTip("Отключить использование прокси")
        self.proxy_none_rb.setChecked(self.parent.proxy_none_rb.isChecked())
        self.proxy_use_rb = QRadioButton("Использовать прокси")
        self.proxy_use_rb.setToolTip("Включить прокси для загрузки")
        self.proxy_use_rb.setChecked(self.parent.proxy_use_rb.isChecked())
        self.proxy_button_group = QButtonGroup()
        self.proxy_button_group.addButton(self.proxy_none_rb)
        self.proxy_button_group.addButton(self.proxy_use_rb)
        layout.addWidget(self.proxy_none_rb)
        layout.addWidget(self.proxy_use_rb)

        proxy_form = QFormLayout()
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["http", "socks4", "socks5"])
        self.proxy_type_combo.setCurrentText(self.parent.proxy_type_combo.currentText())
        self.proxy_type_combo.setToolTip("Тип прокси-сервера")
        self.proxy_address_input = QLineEdit(self.parent.proxy_address_input.text())
        self.proxy_address_input.setPlaceholderText("адрес:порт")
        self.proxy_address_input.setToolTip("Адрес и порт прокси-сервера")
        proxy_form.addRow("Тип прокси:", self.proxy_type_combo)
        proxy_form.addRow("Адрес прокси:", self.proxy_address_input)
        layout.addLayout(proxy_form)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.set_proxy_enabled(self.proxy_use_rb.isChecked())
        self.proxy_none_rb.toggled.connect(lambda: self.set_proxy_enabled(False))
        self.proxy_use_rb.toggled.connect(lambda: self.set_proxy_enabled(True))

    def set_proxy_enabled(self, enabled):
        self.proxy_type_combo.setEnabled(enabled)
        self.proxy_address_input.setEnabled(enabled)

    def save(self):
        self.parent.proxy_none_rb.setChecked(self.proxy_none_rb.isChecked())
        self.parent.proxy_use_rb.setChecked(self.proxy_use_rb.isChecked())
        self.parent.proxy_type_combo.setCurrentText(self.proxy_type_combo.currentText())
        if self.proxy_none_rb.isChecked():
            self.parent.proxy_address_input.clear()  # Очищаем адрес при выборе "Не использовать прокси"
        else:
            self.parent.proxy_address_input.setText(self.proxy_address_input.text())
        self.parent.set_proxy_enabled(self.proxy_use_rb.isChecked())

    def on_accept(self):
        if self.proxy_use_rb.isChecked() and not self.proxy_address_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите адрес прокси (например, 127.0.0.1:8080) или выберите 'Не использовать прокси'")
            return
        self.save()
        self.accept()

class CookiesSettingsDialog(QDialog):
    """Диалоговое окно для настроек cookies."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки cookies")
        self.setMinimumSize(400, 300)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.cookies_none_rb = QRadioButton("Не использовать cookies")
        self.cookies_none_rb.setToolTip("Отключить использование cookies")
        self.cookies_none_rb.setChecked(self.parent.cookies_none_rb.isChecked())
        self.cookies_file_rb = QRadioButton("Использовать файл cookies")
        self.cookies_file_rb.setToolTip("Использовать cookies из файла")
        self.cookies_file_rb.setChecked(self.parent.cookies_file_rb.isChecked())
        self.cookies_browser_rb = QRadioButton("Использовать cookies из браузера")
        self.cookies_browser_rb.setToolTip("Извлечь cookies из браузера")
        self.cookies_browser_rb.setChecked(self.parent.cookies_browser_rb.isChecked())

        # Группируем радиокнопки для взаимоисключения
        self.cookies_button_group = QButtonGroup()
        self.cookies_button_group.addButton(self.cookies_none_rb)
        self.cookies_button_group.addButton(self.cookies_file_rb)
        self.cookies_button_group.addButton(self.cookies_browser_rb)

        layout.addWidget(self.cookies_none_rb)
        layout.addWidget(self.cookies_file_rb)

        self.cookies_file_input = QLineEdit(self.parent.cookies_file_input.text())
        self.cookies_file_input.setToolTip("Путь к файлу cookies")
        self.cookies_file_browse_btn = QPushButton("Обзор...")
        self.cookies_file_browse_btn.setToolTip("Выбрать файл cookies")
        self.cookies_file_browse_btn.clicked.connect(self.browse_cookies)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.cookies_file_input)
        file_layout.addWidget(self.cookies_file_browse_btn)
        layout.addLayout(file_layout)

        layout.addWidget(self.cookies_browser_rb)
        browser_layout = QVBoxLayout()
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(SUPPORTED_BROWSERS)
        self.browser_combo.setCurrentText(self.parent.browser_combo.currentText())
        self.browser_combo.setToolTip("Выберите браузер для извлечения cookies")
        browser_layout.addWidget(self.browser_combo)
        self.browser_profile_input = QLineEdit(self.parent.browser_profile_input.text())
        self.browser_profile_input.setPlaceholderText("Путь к профилю браузера (опционально)")
        self.browser_profile_input.setToolTip("Путь к профилю браузера для извлечения cookies")
        self.browser_profile_browse_btn = QPushButton("Обзор...")
        self.browser_profile_browse_btn.setToolTip("Выбрать папку профиля браузера")
        self.browser_profile_browse_btn.clicked.connect(self.browse_browser_profile)
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(self.browser_profile_input)
        profile_layout.addWidget(self.browser_profile_browse_btn)
        browser_layout.addLayout(profile_layout)
        layout.addLayout(browser_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.set_cookies_enabled(self.get_current_mode())
        self.cookies_none_rb.toggled.connect(lambda: self.set_cookies_enabled('none'))
        self.cookies_file_rb.toggled.connect(lambda: self.set_cookies_enabled('file'))
        self.cookies_browser_rb.toggled.connect(lambda: self.set_cookies_enabled('browser'))

    def get_current_mode(self):
        if self.cookies_file_rb.isChecked():
            return 'file'
        elif self.cookies_browser_rb.isChecked():
            return 'browser'
        return 'none'

    def set_cookies_enabled(self, mode):
        enabled_file = mode == 'file'
        enabled_browser = mode == 'browser'
        self.cookies_file_input.setEnabled(enabled_file)
        self.cookies_file_browse_btn.setEnabled(enabled_file)
        self.browser_combo.setEnabled(enabled_browser)
        self.browser_profile_input.setEnabled(enabled_browser)
        self.browser_profile_browse_btn.setEnabled(enabled_browser)

    def browse_cookies(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл cookies", "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if file:
            self.cookies_file_input.setText(file)

    def browse_browser_profile(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку профиля браузера", self.browser_profile_input.text())
        if path:
            self.browser_profile_input.setText(path)

    def save(self):
        self.parent.cookies_none_rb.setChecked(self.cookies_none_rb.isChecked())
        self.parent.cookies_file_rb.setChecked(self.cookies_file_rb.isChecked())
        self.parent.cookies_browser_rb.setChecked(self.cookies_browser_rb.isChecked())
        
        if self.cookies_none_rb.isChecked():
            self.parent.cookies_file_input.clear()
            self.parent.browser_profile_input.clear()
        elif self.cookies_file_rb.isChecked():
            self.parent.cookies_file_input.setText(self.cookies_file_input.text())
            self.parent.browser_profile_input.clear()
        elif self.cookies_browser_rb.isChecked():
            self.parent.cookies_file_input.clear()
            self.parent.browser_profile_input.setText(self.browser_profile_input.text())
            
        self.parent.browser_combo.setCurrentText(self.browser_combo.currentText())
        self.parent.set_cookies_enabled(self.get_current_mode() != 'none', self.get_current_mode())

    def on_accept(self):
        self.save()
        self.accept()

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
            self.add_to_buffer(f"Запуск команды: {' '.join(cmd)}\n")

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

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        layout = QVBoxLayout()
        label = QLabel(f"yt-dlp GUI\nВерсия {get_version()}\nГрафический интерфейс для yt-dlp")
        layout.addWidget(label)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        self.setLayout(layout)

class YTDLPGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        ConfigManager.init_config()
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
        
        self.init_hidden_widgets()
        self.check_ytdlp_available()
        self.setup_ui()
        self.load_config()

        self.console_update_timer = QTimer(self)
        self.console_update_timer.setInterval(100)
        self.console_update_timer.timeout.connect(self.update_console)

        self.url_input.returnPressed.connect(self.start_download)
        self.paste_btn.setShortcut("Ctrl+V")

    def init_hidden_widgets(self):
        self.path_input = QLineEdit()
        self.template_input = QLineEdit()
        self.merge_combo = QComboBox()
        self.merge_combo.addItems(["mp4", "mkv"])

        self.no_overwrite_check = QCheckBox()
        self.sponsorblock_check = QCheckBox()
        self.metadata_check = QCheckBox()
        self.thumbnail_check = QCheckBox()

        self.proxy_none_rb = QRadioButton()
        self.proxy_use_rb = QRadioButton()
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["http", "socks4", "socks5"])
        self.proxy_address_input = QLineEdit()

        self.cookies_none_rb = QRadioButton()
        self.cookies_file_rb = QRadioButton()
        self.cookies_browser_rb = QRadioButton()
        self.cookies_file_input = QLineEdit()
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(SUPPORTED_BROWSERS)
        self.browser_profile_input = QLineEdit()

    def update_console(self):
        if hasattr(self, 'thread') and self.thread and not self.thread.buffer_lock:
            self.thread.buffer_lock = True
            if self.thread.log_buffer:
                self.console_output.append('\n'.join(self.thread.log_buffer))
                self.thread.log_buffer.clear()
                self.console_output.verticalScrollBar().setValue(
                    self.console_output.verticalScrollBar().maximum()
                )
            self.thread.buffer_lock = False

    def check_ytdlp_available(self):
        if not ConfigManager.check_ytdlp_exists():
            self.status_bar.showMessage("yt-dlp не найден. Скачивание...")
            self.download_ytdlp()

    def download_ytdlp(self):
        url = YTDLP_DOWNLOAD_URL
        if os.name == 'nt':
            url += ".exe"

        destination = ConfigManager.get_ytdlp_path()

        progress_dialog = QProgressDialog("Загрузка yt-dlp...", "Отмена", 0, 100, self)
        progress_dialog.setWindowTitle("Загрузка yt-dlp")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)

        downloader = DownloaderThread(url, destination)
        downloader.progress.connect(progress_dialog.setValue)
        downloader.finished.connect(
            lambda success, msg: self.on_ytdlp_download_finished(success, msg, progress_dialog)
        )
        progress_dialog.canceled.connect(downloader.stop)
        downloader.start()

        progress_dialog.exec()

    def on_ytdlp_download_finished(self, success, message, progress_dialog):
        progress_dialog.close()

        if success:
            if os.name != 'nt':
                os.chmod(ConfigManager.get_ytdlp_path(), 0o755)
            self.status_bar.showMessage("yt-dlp успешно загружен!", 5000)
        else:
            self.status_bar.showMessage(f"Ошибка загрузки: {message}", 5000)

    def check_for_updates(self):
        current_version = ConfigManager.get_ytdlp_version()
        if not current_version:
            self.status_bar.showMessage("Не удалось определить текущую версию yt-dlp", 5000)
            return

        self.status_bar.showMessage("Проверка обновлений...", 3000)

        self.update_checker = UpdateChecker()
        self.update_checker.finished.connect(
            lambda success, msg, latest_version: self.on_update_check_finished(
                success, msg, current_version, latest_version)
        )
        self.update_checker.start()

    def on_update_check_finished(self, success, message, current_version, latest_version):
        if not success:
            self.status_bar.showMessage(f"Ошибка проверки обновлений: {message}", 5000)
            return

        if latest_version and latest_version != current_version:
            reply = QMessageBox.question(
                self,
                "Доступно обновление",
                f"Доступна новая версия yt-dlp: {latest_version}\n"
                f"Текущая версия: {current_version}\n\n"
                "Обновить сейчас?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.download_ytdlp()
        else:
            self.status_bar.showMessage(f"Установлена последняя версия yt-dlp: {current_version}", 5000)

    def setup_ui(self):
        self.setWindowTitle("yt-dlp GUI")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        self.create_menus()
        self.setup_main_interface()
        self.setup_icons()
        self.apply_styles()

    def create_menus(self):
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu("Файл")
        open_log_action = QAction("Открыть лог", self)
        open_log_action.triggered.connect(self.open_log_file)
        file_menu.addAction(open_log_action)

        export_config_action = QAction("Экспорт настроек...", self)
        export_config_action.triggered.connect(self.export_config)
        file_menu.addAction(export_config_action)

        import_config_action = QAction("Импорт настроек...", self)
        import_config_action.triggered.connect(self.import_config)
        file_menu.addAction(import_config_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Правка
        edit_menu = menubar.addMenu("Правка")
        copy_cmd_action = QAction("Копировать команду", self)
        copy_cmd_action.triggered.connect(self.copy_command_line)
        edit_menu.addAction(copy_cmd_action)

        reset_action = QAction("Сбросить настройки", self)
        reset_action.triggered.connect(self.reset_settings)
        edit_menu.addAction(reset_action)

        # Меню Параметры
        params_menu = menubar.addMenu("Параметры")
        
        output_action = QAction("Настройки вывода...", self)
        output_action.triggered.connect(self.show_output_settings)
        params_menu.addAction(output_action)

        proxy_action = QAction("Настройки прокси...", self)
        proxy_action.triggered.connect(self.show_proxy_settings)
        params_menu.addAction(proxy_action)

        cookies_action = QAction("Настройки cookies...", self)
        cookies_action.triggered.connect(self.show_cookies_settings)
        params_menu.addAction(cookies_action)

        # Дополнительные опции (сохраняем текущую реализацию)
        advanced_menu = params_menu.addMenu("Дополнительно")
        
        self.no_overwrite_action = QAction("Не перезаписывать файлы", advanced_menu, checkable=True)
        self.no_overwrite_action.setChecked(self.no_overwrite_check.isChecked())
        self.no_overwrite_action.toggled.connect(lambda checked: self.update_check_state(self.no_overwrite_check, checked))
        advanced_menu.addAction(self.no_overwrite_action)
        
        self.sponsorblock_action = QAction("Удалять спонсорские блоки", advanced_menu, checkable=True)
        self.sponsorblock_action.setChecked(self.sponsorblock_check.isChecked())
        self.sponsorblock_action.toggled.connect(lambda checked: self.update_check_state(self.sponsorblock_check, checked))
        advanced_menu.addAction(self.sponsorblock_action)
        
        self.metadata_action = QAction("Добавлять метаданные", advanced_menu, checkable=True)
        self.metadata_action.setChecked(self.metadata_check.isChecked())
        self.metadata_action.toggled.connect(lambda checked: self.update_check_state(self.metadata_check, checked))
        advanced_menu.addAction(self.metadata_action)
        
        self.thumbnail_action = QAction("Встраивать миниатюру", advanced_menu, checkable=True)
        self.thumbnail_action.setChecked(self.thumbnail_check.isChecked())
        self.thumbnail_action.toggled.connect(lambda checked: self.update_check_state(self.thumbnail_check, checked))
        advanced_menu.addAction(self.thumbnail_action)

        # Меню Инструменты
        tools_menu = menubar.addMenu("Инструменты")
        update_action = QAction("Проверить обновления", self)
        update_action.triggered.connect(self.check_for_updates)
        tools_menu.addAction(update_action)

        # Меню Помощь
        help_menu = menubar.addMenu("Помощь")
        docs_action = QAction("Документация", self)
        docs_action.triggered.connect(self.open_documentation)
        help_menu.addAction(docs_action)

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def update_check_state(self, checkbox, checked):
        checkbox.setChecked(checked)
        self.save_config()

    def show_output_settings(self):
        dialog = OutputSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save()
            self.save_config()
            self.status_bar.showMessage("Настройки вывода обновлены", 3000)

    def show_proxy_settings(self):
        dialog = ProxySettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save()
            self.save_config()
            self.status_bar.showMessage("Настройки прокси обновлены", 3000)

    def show_cookies_settings(self):
        dialog = CookiesSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save()
            self.save_config()
            self.status_bar.showMessage("Настройки cookies обновлены", 3000)

    def setup_main_interface(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        url_group = QGroupBox("Видео для загрузки")
        url_layout = QVBoxLayout(url_group)
        url_layout.setSpacing(8)
        url_layout.setContentsMargins(8, 12, 8, 12)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите URL видео или плейлиста")
        self.url_input.textChanged.connect(self.validate_url)
        url_layout.addWidget(self.url_input)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)
        
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_url)
        
        self.paste_btn = QPushButton("Вставить")
        self.paste_btn.clicked.connect(self.paste_url)
        
        self.download_btn = QPushButton("Скачать")
        self.download_btn.clicked.connect(self.start_download)
        
        self.cancel_btn = QPushButton("Отменить")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        
        self.open_dir_btn = QPushButton("Папка")
        self.open_dir_btn.clicked.connect(self.open_download_folder)
        self.open_dir_btn.setEnabled(False)
        
        for btn in [self.clear_btn, self.paste_btn, self.download_btn, 
                   self.cancel_btn, self.open_dir_btn]:
            btn.setFixedSize(80, 28)
            buttons_layout.addWidget(btn)
        
        buttons_layout.addStretch()
        url_layout.addLayout(buttons_layout)
        main_layout.addWidget(url_group)
        
        console_group = QGroupBox("Вывод")
        console_layout = QVBoxLayout(console_group)
        console_layout.setContentsMargins(8, 12, 8, 12)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText("Здесь будет отображаться ход загрузки...")
        console_layout.addWidget(self.console_output)
        
        main_layout.addWidget(console_group, stretch=1)

    def apply_styles(self):
        style_sheet = """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QMenuBar {
                background-color: white;
                padding: 2px;
                border-bottom: 1px solid #e0e0e0;
            }
            QMenuBar::item {
                padding: 4px 8px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #e0e0e0;
            }
            QMenu {
                background-color: white;
                border: 1px solid #e0e0e0;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                background: white;
                selection-background-color: #e0e0e0;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #4d90fe;
            }
            QLineEdit[valid="false"] {
                border: 1px solid #ff6b6b;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
            }
            QStatusBar {
                background-color: white;
                border-top: 1px solid #e0e0e0;
                padding: 2px;
                font-size: 11px;
            }
            QLabel {
                color: #333;
            }
            QTextEdit {
                font-family: monospace;
                font-size: 10pt;
            }
        """
        self.setStyleSheet(style_sheet)

    def setup_icons(self):
        try:
            self.setWindowIcon(QIcon("assets/icon.ico"))
        except:
            pass

    def paste_url(self):
        clipboard = QGuiApplication.clipboard()
        url = clipboard.text().strip()
        if url:
            self.url_input.setText(url)
            self.status_bar.showMessage("URL вставлен из буфера обмена", 3000)

    def clear_url(self):
        self.url_input.clear()
        self.status_bar.showMessage("Поле URL очищено", 3000)

    def validate_url(self):
        url = self.url_input.text().strip()
        valid = bool(url and re.match(r'^https?://', url))
        self.url_input.setProperty("valid", str(valid).lower())
        self.url_input.style().unpolish(self.url_input)
        self.url_input.style().polish(self.url_input)

    def open_download_folder(self):
        path = self.path_input.text()
        if os.path.exists(path):
            QDesktopServices().openUrl(QUrl.fromLocalFile(path))
            self.status_bar.showMessage(f"Открыта папка: {path}", 3000)
        else:
            self.status_bar.showMessage("Папка не найдена", 5000)

    def load_config(self):
        config_text = ConfigManager.load_config()
        if config_text is None:
            self.template_input.setText("%(title)s.%(ext)s")
            self.path_input.setText(str(Path.home() / "Videos"))
            self.merge_combo.setCurrentText("mp4")
            self.no_overwrite_check.setChecked(True)
            self.sponsorblock_check.setChecked(False)
            self.metadata_check.setChecked(False)
            self.thumbnail_check.setChecked(False)
            self.proxy_none_rb.setChecked(True)
            self.cookies_none_rb.setChecked(True)
        else:
            params = ConfigManager.parse_config(config_text)
            self.template_input.setText(params['output'])
            self.path_input.setText(params['paths'])
            self.merge_combo.setCurrentText(params['merge_format'])

            if params['proxy']:
                self.proxy_use_rb.setChecked(True)
                if '://' in params['proxy']:
                    proto, addr = params['proxy'].split('://')
                    self.proxy_type_combo.setCurrentText(proto)
                    self.proxy_address_input.setText(addr)
            else:
                self.proxy_none_rb.setChecked(True)
                self.proxy_address_input.clear()

            if params['cookies']:
                self.cookies_file_rb.setChecked(True)
                self.cookies_file_input.setText(params['cookies'])
            elif params['cookies_from_browser']:
                self.cookies_browser_rb.setChecked(True)
                if ':' in params['cookies_from_browser']:
                    browser, profile = params['cookies_from_browser'].split(':', 1)
                    self.browser_combo.setCurrentText(browser)
                    self.browser_profile_input.setText(profile)
                else:
                    self.browser_combo.setCurrentText(params['cookies_from_browser'])
                    self.browser_profile_input.clear()
            else:
                self.cookies_none_rb.setChecked(True)
                self.cookies_file_input.clear()
                self.browser_profile_input.clear()

            self.no_overwrite_check.setChecked(params['no_overwrites'])
            self.sponsorblock_check.setChecked(params['sponsorblock_remove'])
            self.metadata_check.setChecked(params['add_metadata'])
            self.thumbnail_check.setChecked(params['embed_thumbnail'])

        # Синхронизация действий меню с чекбоксами
        self.no_overwrite_action.setChecked(self.no_overwrite_check.isChecked())
        self.sponsorblock_action.setChecked(self.sponsorblock_check.isChecked())
        self.metadata_action.setChecked(self.metadata_check.isChecked())
        self.thumbnail_action.setChecked(self.thumbnail_check.isChecked())

    def save_config(self):
        config_lines = []

        config_lines.append(f'--output "{self.template_input.text()}"')
        config_lines.append(f'--paths "{self.path_input.text()}"')
        config_lines.append(f'--merge-output-format {self.merge_combo.currentText()}')

        if self.proxy_use_rb.isChecked() and self.proxy_address_input.text().strip():
            config_lines.append(f'--proxy {self.proxy_type_combo.currentText()}://{self.proxy_address_input.text().strip()}')

        if self.cookies_file_rb.isChecked() and self.cookies_file_input.text().strip():
            config_lines.append(f'--cookies "{self.cookies_file_input.text().strip()}"')
        elif self.cookies_browser_rb.isChecked():
            browser = self.browser_combo.currentText()
            profile = self.browser_profile_input.text().strip()
            if profile:
                config_lines.append(f'--cookies-from-browser {browser}:{profile}')
            else:
                config_lines.append(f'--cookies-from-browser {browser}')

        if self.no_overwrite_check.isChecked():
            config_lines.append('--no-overwrites')
        if self.sponsorblock_check.isChecked():
            config_lines.append('--sponsorblock-remove all')
        if self.metadata_check.isChecked():
            config_lines.append('--add-metadata')
        if self.thumbnail_check.isChecked():
            config_lines.append('--embed-thumbnail')

        config_text = "\n".join(config_lines)
        if ConfigManager.save_config(config_text):
            self.status_bar.showMessage("Конфигурация успешно сохранена", 3000)
            return True
        else:
            self.status_bar.showMessage("Не удалось сохранить конфигурацию", 5000)
            return False

    def set_proxy_enabled(self, enabled):
        """Включает или отключает элементы управления прокси."""
        self.proxy_type_combo.setEnabled(enabled)
        self.proxy_address_input.setEnabled(enabled)

    def set_cookies_enabled(self, enabled, mode=None):
        """Включает или отключает элементы управления cookies."""
        self.cookies_file_input.setEnabled(enabled and mode == 'file')
        self.browser_combo.setEnabled(enabled and mode == 'browser')
        self.browser_profile_input.setEnabled(enabled and mode == 'browser')

    def start_download(self):
        url = self.url_input.text().strip()
        if not url or not re.match(r'^https?://', url):
            self.status_bar.showMessage("Введите корректный URL (начинающийся с http:// или https://)", 5000)
            return

        if not ConfigManager.check_ytdlp_exists():
            self.status_bar.showMessage("yt-dlp не найден. Скачайте его через меню 'Инструменты'", 5000)
            return

        if self.save_config():
            self.status_bar.showMessage("Настройки сохранены. Начинаю загрузку...", 3000)
        else:
            return

        self.console_output.clear()
        self.toggle_controls(False)
        
        self.console_update_timer.start()

        self.thread = DownloadThread(url)
        self.thread.output_received.connect(self.update_console)
        self.thread.finished.connect(self.download_finished)
        self.thread.start()

    def cancel_download(self):
        if hasattr(self, 'thread') and self.thread:
            self.thread.stop()
            self.console_output.append("\nЗагрузка отменена пользователем\n")
            self.toggle_controls(True)
            self.console_update_timer.stop()
            self.status_bar.showMessage("Загрузка отменена", 3000)

    def download_finished(self, success, message):
        QTimer.singleShot(200, self.console_update_timer.stop)
        
        self.update_console()
        
        self.console_output.append(f"\n{message}\n")
        self.toggle_controls(True)

        if success:
            self.status_bar.showMessage("Загрузка завершена успешно!", 5000)
            self.open_dir_btn.setEnabled(True)
        else:
            self.status_bar.showMessage(f"Ошибка загрузки: {message}", 5000)

    def toggle_controls(self, enabled):
        for widget in [self.url_input, self.paste_btn, self.clear_btn, self.download_btn, self.open_dir_btn]:
            widget.setEnabled(enabled)

        self.cancel_btn.setEnabled(not enabled)

    def open_log_file(self):
        if os.path.exists(ConfigManager.LOG_FILE):
            QDesktopServices().openUrl(QUrl.fromLocalFile(ConfigManager.LOG_FILE))
            self.status_bar.showMessage("Файл лога открыт", 3000)
        else:
            self.status_bar.showMessage("Файл лога не найден", 5000)

    def export_config(self):
        file, _ = QFileDialog.getSaveFileName(
            self, "Экспорт настроек", "", "Конфигурационные файлы (*.conf);;Все файлы (*)"
        )
        if file:
            try:
                with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as src, \
                     open(file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                self.status_bar.showMessage("Настройки успешно экспортированы", 5000)
            except Exception as e:
                self.status_bar.showMessage(f"Не удалось экспортировать настройки: {str(e)}", 5000)

    def import_config(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Импорт настроек", "", "Конфигурационные файлы (*.conf);;Все файлы (*)"
        )
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as src, \
                     open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                self.load_config()
                self.status_bar.showMessage("Настройки успешно импортированы", 5000)
            except Exception as e:
                self.status_bar.showMessage(f"Не удалось импортировать настройки: {str(e)}", 5000)

    def copy_command_line(self):
        url = self.url_input.text().strip() or "[URL]"
        cmd = [ConfigManager.get_ytdlp_path(), "--config-location", ConfigManager.CONFIG_FILE, url]
        cmd_text = " ".join(cmd)

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(cmd_text)

        self.status_bar.showMessage("Команда скопирована в буфер обмена", 3000)

    def reset_settings(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                    f.write(ConfigManager.DEFAULT_CONFIG)
                self.load_config()
                self.status_bar.showMessage("Настройки сброшены к значениям по умолчанию", 5000)
            except Exception as e:
                self.status_bar.showMessage(f"Не удалось сбросить настройки: {str(e)}", 5000)

    def open_documentation(self):
        QDesktopServices().openUrl(QUrl("https://github.com/yt-dlp/yt-dlp"))
        self.status_bar.showMessage("Открыта документация в браузере", 3000)

    def show_about(self):
        about_dialog = AboutDialog()
        about_dialog.exec()

    def closeEvent(self, event):
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YTDLPGUI()
    window.show()
    sys.exit(app.exec())
