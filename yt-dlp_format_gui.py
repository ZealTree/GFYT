import sys
import subprocess
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QGroupBox, QTableWidget, QSplitter,
    QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QTextEdit    
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


class FormatFetcher(QThread):
    formats_fetched = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            result = subprocess.run(
                ["yt-dlp", "-j", self.url],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            formats = self.parse_formats(data.get("formats", []))
            self.formats_fetched.emit(formats)
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Error fetching formats: {e.stderr}")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")

    def parse_formats(self, format_list):
        formats = {
            "video_audio": [],
            "video_only": [],
            "audio_only": []
        }

        for fmt in format_list:
            format_id = fmt.get("format_id", "")
            ext = fmt.get("ext", "")
            resolution = fmt.get("resolution", "")
            fps = str(fmt.get("fps", ""))
            filesize_raw = fmt.get("filesize") or fmt.get("filesize_approx")
            filesize = self.format_filesize(filesize_raw) if filesize_raw else ""
            vcodec = fmt.get("vcodec", "")
            acodec = fmt.get("acodec", "")
            vbr = fmt.get("vbr") or fmt.get("tbr") or ""
            abr = fmt.get("abr") or fmt.get("tbr") or ""
            asr = fmt.get("asr", "")

            row = {
                "id": format_id,
                "ext": ext,
                "resolution": resolution,
                "fps": fps,
                "size": filesize,
                "vcodec": vcodec,
                "acodec": acodec,
                "vbitrate": str(vbr),
                "abitrate": str(abr),
                "asr": str(asr),
                "selected": False
            }

            if vcodec != "none" and acodec != "none":
                formats["video_audio"].append(row)
            elif vcodec != "none":
                formats["video_only"].append(row)
            elif acodec != "none":
                formats["audio_only"].append(row)

        return formats

    def format_filesize(self, size):
        if not size:
            return ""
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if size < 1024:
                return f"{size:.2f}{unit}"
            size /= 1024
        return f"{size:.2f}PiB"


class FormatSelectorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp Format Selector")
        self.setMinimumSize(1100, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        self.create_url_input()
        self.create_format_tables()
        self.create_output_section()

        self.current_formats = {
            "video_audio": [],
            "video_only": [],
            "audio_only": []
        }

    def create_url_input(self):
        group = QGroupBox("Video URL")
        layout = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube URL here...")
        self.url_input.returnPressed.connect(self.fetch_formats)
        layout.addWidget(self.url_input)

        self.fetch_button = QPushButton("Get Available Formats")
        self.fetch_button.clicked.connect(self.fetch_formats)
        layout.addWidget(self.fetch_button)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def create_format_tables(self):
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.video_audio_table = self.create_table("Video+Audio", ["Select", "ID", "EXT", "Resolution", "FPS", "Size", "VCodec", "ACodec"])
        splitter.addWidget(self.video_audio_table["group"])

        self.video_only_table = self.create_table("Video Only", ["Select", "ID", "EXT", "Resolution", "FPS", "Size", "VCodec", "VBitrate"])
        splitter.addWidget(self.video_only_table["group"])

        self.audio_only_table = self.create_table("Audio Only", ["Select", "ID", "EXT", "Size", "ACodec", "ABitrate", "ASR"])
        splitter.addWidget(self.audio_only_table["group"])

        splitter.setSizes([300, 250, 250])
        self.main_layout.addWidget(splitter)

    def create_table(self, title, headers):
        group = QGroupBox(title)
        layout = QVBoxLayout()
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSortingEnabled(True)
        layout.addWidget(table)
        group.setLayout(layout)
        return {"group": group, "table": table, "headers": headers}

    def create_output_section(self):
        group = QGroupBox("Download Command")
        layout = QVBoxLayout()

        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMinimumHeight(100)
        self.command_preview.setFont(QFont("Courier New", 10))
        layout.addWidget(self.command_preview)

        self.copy_button = QPushButton("Copy Command")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_button)

        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def fetch_formats(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return

        self.fetch_button.setEnabled(False)
        self.fetch_button.setText("Fetching...")
        self.url_input.setEnabled(False)

        self.fetcher = FormatFetcher(url)
        self.fetcher.formats_fetched.connect(self.on_formats_fetched)
        self.fetcher.error_occurred.connect(self.on_fetch_error)
        self.fetcher.start()

    def on_formats_fetched(self, formats):
        self.current_formats = formats
        self.fetch_button.setEnabled(True)
        self.fetch_button.setText("Get Available Formats")
        self.url_input.setEnabled(True)

        self.update_table(self.video_audio_table["table"], formats["video_audio"], self.video_audio_table["headers"])
        self.update_table(self.video_only_table["table"], formats["video_only"], self.video_only_table["headers"])
        self.update_table(self.audio_only_table["table"], formats["audio_only"], self.audio_only_table["headers"])

    def update_table(self, table, formats, headers):
        table.setRowCount(len(formats))
        for row, fmt in enumerate(formats):
            checkbox = QCheckBox()
            checkbox.setChecked(fmt.get("selected", False))
            checkbox.stateChanged.connect(lambda state, r=row, t=table: self.on_format_selected(state, r, t))
            table.setCellWidget(row, 0, checkbox)

            for col, header in enumerate(headers[1:], start=1):
                key = header.lower()
                value = fmt.get(key, "")
                table.setItem(row, col, QTableWidgetItem(str(value)))

    def on_format_selected(self, state, row, table):
        pass  # Placeholder for future selection logic

    def on_fetch_error(self, error):
        self.fetch_button.setEnabled(True)
        self.fetch_button.setText("Get Available Formats")
        self.url_input.setEnabled(True)
        QMessageBox.critical(self, "Error", error)

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.command_preview.toPlainText())
        QMessageBox.information(self, "Copied", "Command copied to clipboard!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FormatSelectorApp()
    window.show()
    sys.exit(app.exec())
