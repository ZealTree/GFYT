from PyQt6.QtWidgets import QMainWindow, QStatusBar, QTextEdit, QLineEdit, QPushButton, QComboBox, QCheckBox, QRadioButton, QFileDialog, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QProgressDialog
from PyQt6.QtCore import QTimer, QUrl, Qt
from PyQt6.QtGui import QGuiApplication, QAction, QIcon
from .dialogs import OutputSettingsDialog, ProxySettingsDialog, CookiesSettingsDialog, AboutDialog
from .styles import apply_styles
from ..core.config import ConfigManager
from ..core.downloader import DownloaderThread, DownloadThread
from ..core.update_checker import UpdateChecker
from ..core.constants import SUPPORTED_BROWSERS
import os
import shutil
import tempfile
import zipfile
import tarfile
import requests
import sys
import re
from pathlib import Path

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

        self.ffmpeg_location_input = QLineEdit()

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
        url = ConfigManager.YTDLP_DOWNLOAD_URL
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

    def check_for_ytdlp_updates(self):
        current_version = ConfigManager.get_ytdlp_version()
        if not current_version:
            self.status_bar.showMessage("Не удалось определить текущую версию yt-dlp", 5000)
            return

        self.status_bar.showMessage("Проверка обновлений yt-dlp...", 3000)

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

    def check_ffmpeg_availability(self):
        if ConfigManager.check_ffmpeg_exists():
            self.status_bar.showMessage("FFmpeg найден в системе", 5000)
        else:
            self.status_bar.showMessage("FFmpeg не найден. Укажите путь в 'Инструменты -> Указать FFmpeg' или установите FFmpeg", 5000)

    def specify_ffmpeg_location(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку с бинарниками FFmpeg", self.ffmpeg_location_input.text()
        )
        if folder:
            self.ffmpeg_location_input.setText(folder)
            self.save_config()
            self.status_bar.showMessage(f"Путь к FFmpeg установлен: {folder}", 5000)
            if ConfigManager.check_ffmpeg_exists():
                self.status_bar.showMessage("FFmpeg успешно проверен", 5000)
            else:
                self.status_bar.showMessage("FFmpeg не найден в указанной папке", 5000)

    def install_ffmpeg(self):
        reply = QMessageBox.question(
            self,
            "Установка FFmpeg",
            "Скачать и установить FFmpeg из репозитория yt-dlp/FFmpeg-Builds?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                headers = {"User-Agent": ConfigManager.USER_AGENT}
                response = requests.get(ConfigManager.FFMPEG_RELEASES_URL, headers=headers)
                response.raise_for_status()

                release_info = response.json()
                download_url = None
                asset_name = None

                if os.name == 'nt':
                    target = "ffmpeg-master-latest-win64-gpl.zip"
                elif sys.platform == 'darwin':
                    target = "ffmpeg-master-latest-macos64-gpl.zip"
                else:
                    target = "ffmpeg-master-latest-linux64-gpl.tar.xz"

                for asset in release_info['assets']:
                    if asset['name'] == target:
                        download_url = asset['browser_download_url']
                        asset_name = asset['name']
                        break

                if not download_url:
                    self.status_bar.showMessage(f"Не удалось найти сборку FFmpeg ({target})", 5000)
                    return

                self.status_bar.showMessage(f"Скачивание {asset_name}...", 3000)
                self.download_and_install_ffmpeg(download_url)

            except Exception as e:
                self.status_bar.showMessage(f"Ошибка получения сборки FFmpeg: {str(e)}", 5000)

    def download_and_install_ffmpeg(self, download_url):
        temp_dir = tempfile.mkdtemp()
        archive_ext = '.zip' if os.name == 'nt' or sys.platform == 'darwin' else '.tar.xz'
        archive_path = os.path.join(temp_dir, f"ffmpeg{archive_ext}")

        progress_dialog = QProgressDialog("Загрузка FFmpeg...", "Отмена", 0, 100, self)
        progress_dialog.setWindowTitle("Загрузка FFmpeg")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)

        downloader = DownloaderThread(download_url, archive_path)
        downloader.progress.connect(progress_dialog.setValue)
        downloader.finished.connect(
            lambda success, msg: self.on_ffmpeg_download_finished(success, msg, progress_dialog, archive_path, temp_dir)
        )
        progress_dialog.canceled.connect(downloader.stop)
        downloader.start()

        progress_dialog.exec()

    def on_ffmpeg_download_finished(self, success, message, progress_dialog, archive_path, temp_dir):
        progress_dialog.close()

        if not success:
            self.status_bar.showMessage(f"Ошибка загрузки FFmpeg: {message}", 5000)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        archive_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
        if archive_size_mb < 10:
            self.status_bar.showMessage(f"Скачанный архив слишком маленький ({archive_size_mb:.2f} МБ). Возможно, он поврежден.", 5000)
            ConfigManager.log_download(f"Скачанный архив слишком маленький ({archive_size_mb:.2f} МБ). Возможно, он поврежден.", False)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        try:
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                with tarfile.open(archive_path, 'r:xz') as tar_ref:
                    tar_ref.extractall(extract_dir)

            script_dir = os.path.dirname(os.path.abspath(__file__)) if not hasattr(sys, 'frozen') else os.path.dirname(sys.executable)
            ffmpeg_dir = os.path.join(script_dir, "ffmpeg")
            if not os.access(script_dir, os.W_OK):
                self.status_bar.showMessage("Нет прав на запись в директорию скрипта. Укажите другой путь для FFmpeg.", 5000)
                shutil.rmtree(temp_dir, ignore_errors=True)
                return

            os.makedirs(ffmpeg_dir, exist_ok=True)

            ffmpeg_files = ['ffmpeg', 'ffprobe']
            if os.name == 'nt':
                ffmpeg_files = ['ffmpeg.exe', 'ffprobe.exe']

            found_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file in ffmpeg_files:
                        file_path = os.path.join(root, file)
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        ConfigManager.log_download(f"Найден {file} по пути {file_path}, размер: {file_size_mb:.2f} MB")
                        if file_size_mb < 10:
                            self.status_bar.showMessage(f"Файл {file} слишком маленький ({file_size_mb:.2f} МБ). Возможно, архив поврежден.", 5000)
                            ConfigManager.log_download(f"Файл {file} слишком маленький ({file_size_mb:.2f} МБ). Возможно, архив поврежден.", False)
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return
                        found_files.append(file_path)

            if len(found_files) < 2:
                self.status_bar.showMessage("Не удалось найти ffmpeg и/или ffprobe в архиве", 5000)
                shutil.rmtree(temp_dir, ignore_errors=True)
                return

            for src_path in found_files:
                dest_path = os.path.join(ffmpeg_dir, os.path.basename(src_path))
                shutil.move(src_path, dest_path)
                if os.name != 'nt':
                    os.chmod(dest_path, 0o755)
                final_size_mb = os.path.getsize(dest_path) / (1024 * 1024)
                ConfigManager.log_download(f"Перемещен {os.path.basename(src_path)} в {dest_path}, размер: {final_size_mb:.2f} MB")

            self.ffmpeg_location_input.setText(ffmpeg_dir)
            self.save_config()

            if ConfigManager.check_ffmpeg_exists():
                version = ConfigManager.get_ffmpeg_version()
                if version:
                    self.status_bar.showMessage(f"FFmpeg успешно проверен (версия: {version})", 5000)
                else:
                    self.status_bar.showMessage("FFmpeg установлен, но версия не определена", 5000)
            else:
                self.status_bar.showMessage("Установленный FFmpeg недействителен. Укажите другой путь.", 5000)

        except Exception as e:
            self.status_bar.showMessage(f"Ошибка установки FFmpeg: {str(e)}", 5000)
            ConfigManager.log_download(f"Ошибка установки FFmpeg: {str(e)}", False)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def setup_ui(self):
        self.setWindowTitle("yt-dlp GUI")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        self.create_menus()
        self.setup_main_interface()
        self.setup_icons()
        apply_styles(self)

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

        tools_menu = menubar.addMenu("Инструменты")
        
        check_ytdlp_update_action = QAction("Проверить обновление yt-dlp", self)
        check_ytdlp_update_action.triggered.connect(self.check_for_ytdlp_updates)
        tools_menu.addAction(check_ytdlp_update_action)

        check_ffmpeg_action = QAction("Проверить наличие ffmpeg в системе", self)
        check_ffmpeg_action.triggered.connect(self.check_ffmpeg_availability)
        tools_menu.addAction(check_ffmpeg_action)

        specify_ffmpeg_action = QAction("Указать ffmpeg", self)
        specify_ffmpeg_action.triggered.connect(self.specify_ffmpeg_location)
        tools_menu.addAction(specify_ffmpeg_action)

        install_ffmpeg_action = QAction("Установить ffmpeg", self)
        install_ffmpeg_action.triggered.connect(self.install_ffmpeg)
        tools_menu.addAction(install_ffmpeg_action)

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

    def setup_icons(self):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Ошибка загрузки иконки: {e}")

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
        from PyQt6.QtGui import QDesktopServices
        path = self.path_input.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
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
            self.ffmpeg_location_input.clear()
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
            self.ffmpeg_location_input.setText(params['ffmpeg_location'] or "")

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

        if self.ffmpeg_location_input.text().strip():
            config_lines.append(f'--ffmpeg-location "{self.ffmpeg_location_input.text().strip()}"')

        config_text = "\n".join(config_lines)
        if ConfigManager.save_config(config_text):
            self.status_bar.showMessage("Конфигурация успешно сохранена", 3000)
            return True
        else:
            self.status_bar.showMessage("Не удалось сохранить конфигурацию", 5000)
            return False

    def set_proxy_enabled(self, enabled):
        self.proxy_type_combo.setEnabled(enabled)
        self.proxy_address_input.setEnabled(enabled)

    def set_cookies_enabled(self, enabled, mode=None):
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
        from PyQt6.QtGui import QDesktopServices
        if os.path.exists(ConfigManager.LOG_FILE):
            QDesktopServices.openUrl(QUrl.fromLocalFile(ConfigManager.LOG_FILE))
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
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl("https://github.com/yt-dlp/yt-dlp"))
        self.status_bar.showMessage("Открыта документация в браузере", 3000)

    def show_about(self):
        about_dialog = AboutDialog()
        about_dialog.exec()

    def closeEvent(self, event):
        super().closeEvent(event)