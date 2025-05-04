from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QComboBox, QCheckBox, QRadioButton, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QDialogButtonBox, QHeaderView, QFormLayout, QButtonGroup
from PyQt6.QtCore import Qt
from ..core.constants import SUPPORTED_BROWSERS
from ..utils.file_utils import get_version
import os

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
            self.parent.proxy_address_input.clear()
        else:
            self.parent.proxy_address_input.setText(self.proxy_address_input.text())

    def on_accept(self):
        if self.proxy_use_rb.isChecked() and not self.proxy_address_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите адрес прокси (например, 127.0.0.1:8080) или выберите 'Не использовать прокси'")
            return
        self.save()
        self.accept()

class CookiesSettingsDialog(QDialog):
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