def apply_styles(widget):
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
    widget.setStyleSheet(style_sheet)