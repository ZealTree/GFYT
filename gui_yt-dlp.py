import os
import sys
import json
import subprocess
import requests
import re
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
                            QGroupBox, QTextEdit, QFileDialog, QMessageBox, QProgressDialog,
                            QRadioButton, QButtonGroup, QFormLayout, QMenuBar, QMenu, QAction,
                            QDialog, QPlainTextEdit, QTableWidget, QTableWidgetItem,
                            QDialogButtonBox, QHeaderView, QStatusBar)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSettings, QUrl, QTimer
from PyQt5.QtGui import QDesktopServices, QIcon

# Проверка зависимостей
try:
    import PyQt5
    import requests
except ImportError as e:
    print(f"Ошибка: Необходимая библиотека не установлена: {e}")
    print("Установите зависимости с помощью: pip install PyQt5 requests")
    sys.exit(1)

# Константы
YTDLP_RELEASES_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
USER_AGENT = "yt-dlp-gui/1.0"
SUPPORTED_BROWSERS = ["brave", "chrome", "firefox", "vivaldi"]

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
        """Останавливает загрузку."""
        self._is_running = False

class ConfigManager:
    CONFIG_FILE = "yt-dlp.conf"
    LOG_FILE = "yt-dlp-gui.log"
    SETTINGS_FILE = "gui-settings.ini"

    DEFAULT_CONFIG = """# yt-dlp Configuration File
--output "%(title)s.%(ext)s"
--paths "{}/Videos"
--merge-output-format mp4
--no-overwrites
""".format(str(Path.home()))

    @classmethod
    def init_config(cls):
        """Инициализирует конфигурационные файлы при первом запуске."""
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
        """Парсит конфиг в словарь параметров."""
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
                params['cookies_from_browser'] = line.split()[-1]
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
        """Логирует информацию о загрузке."""
        with open(cls.LOG_FILE, 'a', encoding='utf-8') as f:
            status = "SUCCESS" if success else "FAILED"
            f.write(f"[{datetime.now()}] {status} - {url}\n")

    @classmethod
    def get_ytdlp_path(cls):
        """Возвращает путь к yt-dlp в зависимости от ОС."""
        if os.name == 'nt':
            return "yt-dlp.exe"
        return "./yt-dlp"

    @classmethod
    def check_ytdlp_exists(cls):
        """Проверяет наличие yt-dlp."""
        return os.path.exists(cls.get_ytdlp_path())

    @classmethod
    def get_ytdlp_version(cls):
        """Получает версию yt-dlp."""
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
    finished = pyqtSignal(bool, str, str)  # success, message, latest_version

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
    """Диалоговое окно для редактирования шаблона имени файла."""
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

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.template_edit.textChanged.connect(self.update_preview)

    def setup_variables_table(self):
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(3)
        self.variables_table.setHorizontalHeaderLabels(["Переменная", "Описание", "Действие"])
        self.variables_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.variables_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.variables_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
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

class AboutDialog(QDialog):
    """Диалоговое окно 'О программе'."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("О программе")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        title = QLabel("yt-dlp GUI")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        version = QLabel(f"Версия: Built on {datetime.now().strftime('%y%m%d_%H%M%S')} (PyQt5)")
        layout.addWidget(version)

        desc = QLabel("Графический интерфейс для yt-dlp\n\n"
                      "Использует официальный yt-dlp\n"
                      "Лицензия: MIT")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        github = QLabel("<a href='https://github.com/yt-dlp/yt-dlp'>GitHub</a>")
        github.setOpenExternalLinks(True)
        layout.addWidget(github)

        self.setLayout(layout)

class DebugConsole(QDialog):
    """Консоль отладки."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Консоль отладки")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout()
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        self.setLayout(layout)

    def append_log(self, message):
        self.console.appendPlainText(message)

class DownloadThread(QThread):
    output_received = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self._is_running = True
        self.process = None
        self.log_buffer = []  # Буфер для хранения логов
        self.buffer_lock = False  # Флаг блокировки буфера

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
        """Добавляет сообщение в буфер логов."""
        while self.buffer_lock:  # Ждем, если буфер заблокирован
            QThread.msleep(10)
        self.buffer_lock = True
        self.log_buffer.append(message)
        self.buffer_lock = False
        self.output_received.emit("")  # Сигнализируем о новом сообщении

    def stop(self):
        """Останавливает процесс загрузки."""
        self._is_running = False
        if self.process:
            self.process.terminate()

class YTDLPGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        ConfigManager.init_config()
        
        # Настройка статус-бара
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
        
        self.check_ytdlp_available()
        self.setup_ui()
        self.load_config()

        self.debug_console = DebugConsole()
        self.settings = QSettings(ConfigManager.SETTINGS_FILE, QSettings.IniFormat)
        self.load_gui_settings()

        # Таймер для обновления консоли
        self.console_update_timer = QTimer(self)
        self.console_update_timer.setInterval(100)  # Обновляем каждые 100 мс
        self.console_update_timer.timeout.connect(self.update_console)
        self.pending_updates = False  # Флаг наличия обновлений

    def update_console(self):
        """Обновляет консоль из буфера."""
        if hasattr(self, 'thread') and self.thread and not self.thread.buffer_lock:
            self.thread.buffer_lock = True
            if self.thread.log_buffer:
                self.console_output.append('\n'.join(self.thread.log_buffer))
                self.thread.log_buffer.clear()
                # Прокручиваем вниз
                self.console_output.verticalScrollBar().setValue(
                    self.console_output.verticalScrollBar().maximum()
                )
            self.thread.buffer_lock = False
            self.pending_updates = False
        elif self.pending_updates:
            self.pending_updates = False

    def check_ytdlp_available(self):
        """Проверяет наличие yt-dlp и предлагает скачать, если его нет."""
        if not ConfigManager.check_ytdlp_exists():
            self.status_bar.showMessage("yt-dlp не найден. Скачивание...")
            self.download_ytdlp()

    def download_ytdlp(self):
        """Скачивает yt-dlp."""
        url = YTDLP_DOWNLOAD_URL
        if os.name == 'nt':
            url += ".exe"

        destination = ConfigManager.get_ytdlp_path()

        progress_dialog = QProgressDialog("Загрузка yt-dlp...", "Отмена", 0, 100, self)
        progress_dialog.setWindowTitle("Загрузка yt-dlp")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setAutoClose(True)

        downloader = DownloaderThread(url, destination)
        downloader.progress.connect(progress_dialog.setValue)
        downloader.finished.connect(
            lambda success, msg: self.on_ytdlp_download_finished(success, msg, progress_dialog)
        )
        progress_dialog.canceled.connect(downloader.stop)
        downloader.start()

        progress_dialog.exec_()

    def on_ytdlp_download_finished(self, success, message, progress_dialog):
        """Обработчик завершения загрузки yt-dlp."""
        progress_dialog.close()

        if success:
            if os.name != 'nt':
                os.chmod(ConfigManager.get_ytdlp_path(), 0o755)
            self.status_bar.showMessage("yt-dlp успешно загружен!", 5000)
        else:
            self.status_bar.showMessage(f"Ошибка загрузки: {message}", 5000)

    def check_for_updates(self):
        """Проверяет наличие обновлений yt-dlp."""
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
        """Обработчик завершения проверки обновлений."""
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
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.download_ytdlp()
        else:
            self.status_bar.showMessage(f"Установлена последняя версия yt-dlp: {current_version}", 5000)

    def setup_ui(self):
        self.setWindowTitle("yt-dlp GUI")
        self.setMinimumSize(1000, 700)  # Увеличенный размер для горизонтального расположения

        self.create_menus()
        self.setup_main_interface()
        self.setup_icons()

    def create_menus(self):
        menubar = self.menuBar()

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

        edit_menu = menubar.addMenu("Правка")
        copy_cmd_action = QAction("Копировать команду", self)
        copy_cmd_action.triggered.connect(self.copy_command_line)
        edit_menu.addAction(copy_cmd_action)

        reset_action = QAction("Сбросить настройки", self)
        reset_action.triggered.connect(self.reset_settings)
        edit_menu.addAction(reset_action)

        tools_menu = menubar.addMenu("Инструменты")
        update_action = QAction("Проверить обновления", self)
        update_action.triggered.connect(self.check_for_updates)
        tools_menu.addAction(update_action)

        debug_action = QAction("Консоль отладки", self)
        debug_action.triggered.connect(self.show_debug_console)
        tools_menu.addAction(debug_action)

        help_menu = menubar.addMenu("Помощь")
        docs_action = QAction("Документация", self)
        docs_action.triggered.connect(self.open_documentation)
        help_menu.addAction(docs_action)

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_main_interface(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # URL Input
        url_group = QGroupBox("Видео для загрузки")
        url_layout = QVBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите URL видео или плейлиста")
        url_layout.addWidget(self.url_input)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # Создаем горизонтальный контейнер для "Настройки вывода" и "Дополнительные опции"
        output_options_layout = QHBoxLayout()
        output_options_layout.setSpacing(10)  # Отступ между боксами

        # Output Settings
        output_group = QGroupBox("Настройки вывода")
        output_layout = QVBoxLayout()

        # Output path
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_browse_btn = QPushButton("Обзор...")
        self.path_browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.path_browse_btn)
        output_layout.addLayout(path_layout)

        # Output template
        template_layout = QHBoxLayout()
        self.template_input = QLineEdit()
        self.template_btn = QPushButton("Конструктор...")
        self.template_btn.clicked.connect(self.edit_template)
        template_layout.addWidget(self.template_input)
        template_layout.addWidget(self.template_btn)
        output_layout.addWidget(QLabel("Шаблон имени файла:"))
        output_layout.addLayout(template_layout)

        # Merge format
        self.merge_combo = QComboBox()
        self.merge_combo.addItems(["mp4", "mkv"])
        output_layout.addWidget(QLabel("Формат объединения:"))
        output_layout.addWidget(self.merge_combo)

        output_group.setLayout(output_layout)
        output_options_layout.addWidget(output_group, stretch=2)  # Больше места для "Настройки вывода"

        # Options
        options_group = QGroupBox("Дополнительные опции")
        options_layout = QVBoxLayout()

        self.no_overwrite_check = QCheckBox("Не перезаписывать существующие файлы")
        options_layout.addWidget(self.no_overwrite_check)

        self.sponsorblock_check = QCheckBox("Удалять спонсорские блоки")
        options_layout.addWidget(self.sponsorblock_check)

        self.metadata_check = QCheckBox("Добавлять метаданные")
        options_layout.addWidget(self.metadata_check)

        self.thumbnail_check = QCheckBox("Встраивать миниатюру")
        options_layout.addWidget(self.thumbnail_check)

        options_group.setLayout(options_layout)
        output_options_layout.addWidget(options_group, stretch=1)  # Меньше места для "Дополнительные опции"

        # Добавляем горизонтальный контейнер в основной layout
        layout.addLayout(output_options_layout)

        # Proxy and Cookies Settings
        proxy_cookies_layout = QHBoxLayout()

        proxy_group = QGroupBox("Настройки прокси")
        proxy_layout = QVBoxLayout()

        self.proxy_none_rb = QRadioButton("Не использовать прокси")
        self.proxy_none_rb.setChecked(True)
        self.proxy_use_rb = QRadioButton("Использовать прокси")

        self.proxy_button_group = QButtonGroup()
        self.proxy_button_group.addButton(self.proxy_none_rb)
        self.proxy_button_group.addButton(self.proxy_use_rb)

        proxy_layout.addWidget(self.proxy_none_rb)
        proxy_layout.addWidget(self.proxy_use_rb)

        proxy_form = QFormLayout()

        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["http", "socks4", "socks5"])

        self.proxy_address_input = QLineEdit()
        self.proxy_address_input.setPlaceholderText("адрес:порт")

        proxy_form.addRow("Тип прокси:", self.proxy_type_combo)
        proxy_form.addRow("Адрес прокси:", self.proxy_address_input)

        proxy_layout.addLayout(proxy_form)
        proxy_group.setLayout(proxy_layout)
        proxy_cookies_layout.addWidget(proxy_group, 1)

        cookies_group = QGroupBox("Настройки cookies")
        cookies_layout = QVBoxLayout()

        self.cookies_none_rb = QRadioButton("Не использовать cookies")
        self.cookies_none_rb.setChecked(True)
        self.cookies_file_rb = QRadioButton("Использовать файл cookies")
        self.cookies_browser_rb = QRadioButton("Использовать cookies из браузера")

        cookies_layout.addWidget(self.cookies_none_rb)
        cookies_layout.addWidget(self.cookies_file_rb)

        self.cookies_file_input = QLineEdit()
        self.cookies_file_browse_btn = QPushButton("Обзор...")
        self.cookies_file_browse_btn.clicked.connect(self.browse_cookies)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.cookies_file_input)
        file_layout.addWidget(self.cookies_file_browse_btn)
        cookies_layout.addLayout(file_layout)

        cookies_layout.addWidget(self.cookies_browser_rb)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(SUPPORTED_BROWSERS)
        cookies_layout.addWidget(self.browser_combo)

        cookies_group.setLayout(cookies_layout)
        proxy_cookies_layout.addWidget(cookies_group, 1)

        layout.addLayout(proxy_cookies_layout)

        # Console Output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText("Здесь будет отображаться ход загрузки...")
        layout.addWidget(self.console_output)

        # Buttons
        btn_layout = QHBoxLayout()
        self.download_btn = QPushButton("Загрузить")
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn = QPushButton("Отменить")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Initial state
        self.set_proxy_enabled(False)
        self.set_cookies_enabled(False)

        # Connect signals
        self.proxy_none_rb.toggled.connect(lambda: self.set_proxy_enabled(False))
        self.proxy_use_rb.toggled.connect(lambda: self.set_proxy_enabled(True))
        self.cookies_none_rb.toggled.connect(lambda: self.set_cookies_enabled(False))
        self.cookies_file_rb.toggled.connect(lambda: self.set_cookies_enabled(True, 'file'))
        self.cookies_browser_rb.toggled.connect(lambda: self.set_cookies_enabled(True, 'browser'))

    def setup_icons(self):
        """Устанавливает иконки окна, если они доступны."""
        try:
            self.setWindowIcon(QIcon("icon.png"))
        except:
            pass

    def edit_template(self):
        """Открывает диалог редактирования шаблона."""
        dialog = TemplateEditorDialog(self.template_input.text(), self)
        if dialog.exec_() == QDialog.Accepted:
            self.template_input.setText(dialog.get_template())

    def load_config(self):
        """Загружает конфигурацию в GUI."""
        config_text = ConfigManager.load_config()
        if config_text is None:
            return

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

        if params['cookies']:
            self.cookies_file_rb.setChecked(True)
            self.cookies_file_input.setText(params['cookies'])
        elif params['cookies_from_browser']:
            self.cookies_browser_rb.setChecked(True)
            self.browser_combo.setCurrentText(params['cookies_from_browser'])

        self.no_overwrite_check.setChecked(params['no_overwrites'])
        self.sponsorblock_check.setChecked(params['sponsorblock_remove'])
        self.metadata_check.setChecked(params['add_metadata'])
        self.thumbnail_check.setChecked(params['embed_thumbnail'])

    def save_config(self):
        """Сохраняет текущие настройки GUI в конфигурационный файл."""
        config_lines = []

        config_lines.append(f'--output "{self.template_input.text()}"')
        config_lines.append(f'--paths "{self.path_input.text()}"')
        config_lines.append(f'--merge-output-format {self.merge_combo.currentText()}')

        if self.proxy_use_rb.isChecked() and self.proxy_address_input.text():
            config_lines.append(f'--proxy {self.proxy_type_combo.currentText()}://{self.proxy_address_input.text()}')

        if self.cookies_file_rb.isChecked() and self.cookies_file_input.text():
            config_lines.append(f'--cookies "{self.cookies_file_input.text()}"')
        elif self.cookies_browser_rb.isChecked():
            config_lines.append(f'--cookies-from-browser {self.browser_combo.currentText()}')

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
        self.cookies_file_browse_btn.setEnabled(enabled and mode == 'file')
        self.browser_combo.setEnabled(enabled and mode == 'browser')

    def browse_path(self):
        """Открывает диалог выбора пути сохранения."""
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения", self.path_input.text())
        if path:
            if os.access(path, os.W_OK):
                self.path_input.setText(path)
                self.status_bar.showMessage(f"Выбрана папка: {path}", 3000)
            else:
                self.status_bar.showMessage("Нет прав на запись в выбранную папку", 5000)

    def browse_cookies(self):
        """Открывает диалог выбора файла cookies."""
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл cookies", "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if file:
            self.cookies_file_input.setText(file)
            self.status_bar.showMessage(f"Выбран файл cookies: {file}", 3000)

    def start_download(self):
        """Запускает процесс загрузки видео."""
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
        self.thread.output_received.connect(lambda: setattr(self, 'pending_updates', True))
        self.thread.finished.connect(self.download_finished)
        self.thread.start()

    def cancel_download(self):
        """Отменяет текущую загрузку."""
        if hasattr(self, 'thread') and self.thread:
            self.thread.stop()
            self.console_output.append("\nЗагрузка отменена пользователем\n")
            self.toggle_controls(True)
            self.console_update_timer.stop()
            self.status_bar.showMessage("Загрузка отменена", 3000)

    def download_finished(self, success, message):
        """Обрабатывает завершение загрузки."""
        QTimer.singleShot(200, self.console_update_timer.stop)
        
        self.update_console()
        
        self.console_output.append(f"\n{message}\n")
        self.toggle_controls(True)

        if success:
            self.status_bar.showMessage("Загрузка завершена успешно!", 5000)
        else:
            self.status_bar.showMessage(f"Ошибка загрузки: {message}", 5000)

    def toggle_controls(self, enabled):
        """Включает или отключает элементы управления GUI во время загрузки."""
        for widget in [
            self.url_input, self.path_input, self.path_browse_btn,
            self.template_input, self.template_btn, self.merge_combo,
            self.proxy_none_rb, self.proxy_use_rb,
            self.proxy_type_combo, self.proxy_address_input,
            self.cookies_none_rb, self.cookies_file_rb, self.cookies_browser_rb,
            self.cookies_file_input, self.cookies_file_browse_btn, self.browser_combo,
            self.no_overwrite_check, self.sponsorblock_check,
            self.metadata_check, self.thumbnail_check, self.download_btn
        ]:
            widget.setEnabled(enabled)

        self.cancel_btn.setEnabled(not enabled)
        self.set_proxy_enabled(enabled and self.proxy_use_rb.isChecked())

        mode = None
        if self.cookies_file_rb.isChecked():
            mode = 'file'
        elif self.cookies_browser_rb.isChecked():
            mode = 'browser'
        self.set_cookies_enabled(enabled and mode is not None, mode)

    def open_log_file(self):
        """Открывает файл логов."""
        if os.path.exists(ConfigManager.LOG_FILE):
            QDesktopServices.openUrl(QUrl.fromLocalFile(ConfigManager.LOG_FILE))
            self.status_bar.showMessage("Файл лога открыт", 3000)
        else:
            self.status_bar.showMessage("Файл лога не найден", 5000)

    def export_config(self):
        """Экспортирует текущую конфигурацию в файл."""
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
        """Импортирует конфигурацию из файла."""
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
        """Копирует командную строку в буфер обмена."""
        url = self.url_input.text().strip() or "[URL]"
        cmd = [ConfigManager.get_ytdlp_path(), "--config-location", ConfigManager.CONFIG_FILE, url]
        cmd_text = " ".join(cmd)

        clipboard = QApplication.clipboard()
        clipboard.setText(cmd_text)

        self.status_bar.showMessage("Команда скопирована в буфер обмена", 3000)

    def reset_settings(self):
        """Сбрасывает настройки до значений по умолчанию."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                    f.write(ConfigManager.DEFAULT_CONFIG)
                self.load_config()
                self.status_bar.showMessage("Настройки сброшены к значениям по умолчанию", 5000)
            except Exception as e:
                self.status_bar.showMessage(f"Не удалось сбросить настройки: {str(e)}", 5000)

    def show_debug_console(self):
        """Показывает консоль отладки."""
        self.debug_console.show()
        self.status_bar.showMessage("Открыта консоль отладки", 3000)

    def open_documentation(self):
        """Открывает документацию в браузере."""
        QDesktopServices.openUrl(QUrl("https://github.com/yt-dlp/yt-dlp"))
        self.status_bar.showMessage("Открыта документация в браузере", 3000)

    def show_about(self):
        """Показывает диалог 'О программе'."""
        about_dialog = AboutDialog()
        about_dialog.exec_()

    def load_gui_settings(self):
        """Загружает настройки GUI (размер окна, позиция и т.д.)."""
        geometry = self.settings.value("windowGeometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state is not None:
            self.restoreState(state)

    def save_gui_settings(self):
        """Сохраняет настройки GUI перед закрытием."""
        self.settings.setValue("windowGeometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

    def closeEvent(self, event):
        self.save_gui_settings()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YTDLPGUI()
    window.show()
    sys.exit(app.exec_())