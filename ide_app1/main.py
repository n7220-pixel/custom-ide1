# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt for more information.

# Imports
import json
import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QProcess, QRect, QSize, Qt
from PyQt6.QtGui import QMouseEvent, QPainter, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Fix import path
from languageSupport.syntax import create_highlighter

Version = "2.0.0"


# Clickable status bar label
class ClickableLabel(QLabel):
    def __init__(self, text: str = "", parent: Optional[QLabel] = None):
        super().__init__(text, parent)
        self.menu = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setMenu(self, menu):
        self.menu = menu

    # 1. Use Optional[QMouseEvent] to match the base class signature
    # 2. Add -> None to specify the return type
    def mousePressEvent(self, ev: Optional[QMouseEvent]) -> None:
        # Check that ev is not None before accessing it
        if ev and self.menu and ev.button() == Qt.MouseButton.LeftButton:
            # PyQt6: position() replaces pos(), and we must cast to integer point
            self.menu.exec(self.mapToGlobal(ev.position().toPoint()))

        # Ensure we pass the event to the parent class
        super().mousePressEvent(ev)


# Settings Manager
class Settings:
    def __init__(self, base_path):
        self.base_path = base_path
        self.settings_file = base_path / "settings.json"
        self.defaults_file = base_path / "defaults" / "settings.json"
        self.data = self.load()

    def load(self):
        # Try user settings first, then defaults
        if self.settings_file.exists():
            try:
                return json.loads(self.settings_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        if self.defaults_file.exists():
            try:
                return json.loads(self.defaults_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return self._default_settings()

    def save(self):
        self.settings_file.write_text(json.dumps(self.data, indent=4), encoding="utf-8")

    def _default_settings(self):
        return {
            "version": Version,
            "mode": "full",
            "editor": {
                "fontSize": 11,
                "tabSize": 4,
                "wordWrap": False,
                "fontFamily": "Roboto Mono",
            },
            "terminal": {"fontSize": 10, "fontFamily": "Roboto Mono"},
            "appearance": {"theme": "dark", "useSystemFont": False},
            "keybinds": {
                "newFile": "Ctrl+N",
                "openFile": "Ctrl+O",
                "save": "Ctrl+S",
                "saveAs": "Ctrl+Shift+S",
                "exit": "Ctrl+Q",
                "undo": "Ctrl+Z",
                "redo": "Ctrl+Shift+Z",
                "zoomIn": "Ctrl++",
                "zoomOut": "Ctrl+-",
                "resetZoom": "Ctrl+0",
                "toggleSidebar": "Ctrl+B",
                "toggleTerminal": "Ctrl+`",
            },
            "recentFiles": [],
            "recentFolders": [],
            "window": {
                "width": 1100,
                "height": 800,
                "sidebarWidth": 250,
                "terminalHeight": 200,
            },
        }

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys, value):
        data = self.data
        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]
        data[keys[-1]] = value

    def add_recent_file(self, path):
        recent = self.data.get("recentFiles", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.data["recentFiles"] = recent[:10]  # Keep last 10
        self.save()

    def add_recent_folder(self, path):
        recent = self.data.get("recentFolders", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.data["recentFolders"] = recent[:5]  # Keep last 5
        self.save()

    def detect_mode(self):
        # Detect appropriate mode based on environment
        mode = self.data.get("mode", "full")

        # Check for restricted environment indicators
        if os.environ.get("IDE_SAFE_MODE"):
            return "safe"
        if os.environ.get("IDE_RESTRICTED_MODE"):
            return "restricted"

        # Check write permissions
        try:
            test_file = self.base_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
        except (PermissionError, OSError):
            return "safe"

        return mode

    def export_settings(self, path):
        Path(path).write_text(json.dumps(self.data, indent=4), encoding="utf-8")

    def import_settings(self, path):
        try:
            imported = json.loads(Path(path).read_text(encoding="utf-8"))
            self.data = imported
            self.save()
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False


# Line number area
class LineNumberWidget(QWidget):
    def __init__(self, Editor):
        super().__init__(Editor)
        self.setObjectName("lineNumberArea")
        self.Editor = Editor

    def sizeHint(self):
        return QSize(self.Editor.LineNumberWidth(), 0)

    def paintEvent(self, a0):
        self.Editor.PaintLineNumbers(a0)


# Code editor
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()

        self.setObjectName("codeEditor")
        self.LineNumbers = LineNumberWidget(self)
        self.Highlighter = None
        self.Language = "Plain text"

        TabSpaceAmount = " " * 11

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(TabSpaceAmount))

        self.blockCountChanged.connect(self.UpdateLineNumberWidth)
        self.updateRequest.connect(self.UpdateLineNumbers)

        self.UpdateLineNumberWidth(0)

    def setLanguage(self, file_path):
        """Sets language by file path"""
        if self.Highlighter:
            self.Highlighter.setDocument(None)

        self.Highlighter, self.Language = create_highlighter(self.document(), file_path)

    def LineNumberWidth(self):
        Digits = len(str(max(1, self.blockCount())))
        return 35 + self.fontMetrics().horizontalAdvance("9") * Digits

    def UpdateLineNumberWidth(self, _):
        self.setViewportMargins(self.LineNumberWidth(), 0, 0, 0)

    def UpdateLineNumbers(self, Rect, Dy):
        if Dy:
            self.LineNumbers.scroll(0, Dy)
        else:
            self.LineNumbers.update(
                0, Rect.y(), self.LineNumbers.width(), Rect.height()
            )

    def resizeEvent(self, e):
        super().resizeEvent(e)
        Cr = self.contentsRect()
        self.LineNumbers.setGeometry(
            QRect(Cr.left(), Cr.top(), self.LineNumberWidth(), Cr.height())
        )

    def PaintLineNumbers(self, Event):
        Painter = QPainter(self.LineNumbers)
        Painter.fillRect(Event.rect(), self.LineNumbers.palette().window())
        Painter.setPen(self.LineNumbers.palette().text().color())

        Block = self.firstVisibleBlock()
        Number = Block.blockNumber()
        Top = int(
            self.blockBoundingGeometry(Block).translated(self.contentOffset()).top()
        )
        Bottom = Top + int(self.blockBoundingRect(Block).height())

        while Block.isValid() and Top <= Event.rect().bottom():
            if Block.isVisible() and Bottom >= Event.rect().top():
                Painter.drawText(
                    0,
                    Top,
                    self.LineNumbers.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(Number + 1),
                )
            Block = Block.next()
            Top = Bottom
            Bottom = Top + int(self.blockBoundingRect(Block).height())
            Number += 1


# OS Terminal widget
class TerminalWidget(QWidget):
    def __init__(self, Parent=None):
        super().__init__(Parent)
        self.setObjectName("terminalWidget")

        self.Process = QProcess(self)
        self.Process.readyReadStandardOutput.connect(self.HandleStdout)
        self.Process.readyReadStandardError.connect(self.HandleStderr)

        self.Layout = QVBoxLayout(self)
        self.Layout.setContentsMargins(0, 0, 0, 0)
        self.Layout.setSpacing(0)

        self.OutputArea = QPlainTextEdit()
        self.OutputArea.setObjectName("terminalOutput")
        self.OutputArea.setReadOnly(True)

        self.InputArea = QLineEdit()
        self.InputArea.setObjectName("terminalInput")
        self.InputArea.setPlaceholderText("Enter command...")
        self.InputArea.returnPressed.connect(self.SendCommand)

        self.Layout.addWidget(self.OutputArea)
        self.Layout.addWidget(self.InputArea)

        self.OutputArea.appendPlainText(f"Terminal Initialized in {os.getcwd()}\n")

    def SendCommand(self):
        Command = self.InputArea.text()
        if not Command.strip():
            return

        self.OutputArea.appendPlainText(f"$ {Command}")

        # Determine shell based on OS
        Shell = "cmd.exe" if os.name == "nt" else "/bin/bash"
        Args = ["/c", Command] if os.name == "nt" else ["-c", Command]

        self.Process.start(Shell, Args)
        self.InputArea.clear()

    def HandleStdout(self):
        Data = self.Process.readAllStandardOutput().data().decode()
        self.OutputArea.appendPlainText(Data)
        self.ScrollToBottom()

    def HandleStderr(self):
        Data = self.Process.readAllStandardError().data().decode()
        self.OutputArea.appendPlainText(f"Error: {Data}")
        self.ScrollToBottom()

    def ScrollToBottom(self):
        self.OutputArea.moveCursor(QTextCursor.MoveOperation.End)


# Settings Dialog
class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Editor settings
        self.fontSizeSpin = QSpinBox()
        self.fontSizeSpin.setRange(6, 72)
        self.fontSizeSpin.setValue(settings.get("editor", "fontSize", default=11))
        form.addRow("Editor Font Size:", self.fontSizeSpin)

        self.tabSizeSpin = QSpinBox()
        self.tabSizeSpin.setRange(1, 8)
        self.tabSizeSpin.setValue(settings.get("editor", "tabSize", default=4))
        form.addRow("Tab Size:", self.tabSizeSpin)

        self.wordWrapCheck = QCheckBox()
        self.wordWrapCheck.setChecked(settings.get("editor", "wordWrap", default=False))
        form.addRow("Word Wrap:", self.wordWrapCheck)

        self.systemFontCheck = QCheckBox()
        self.systemFontCheck.setChecked(
            settings.get("appearance", "useSystemFont", default=False)
        )
        form.addRow("Use System Font:", self.systemFontCheck)

        # Mode selection
        self.modeCombo = QComboBox()
        self.modeCombo.addItems(["full", "restricted", "safe"])
        self.modeCombo.setCurrentText(settings.get("mode", default="full"))
        form.addRow("Mode:", self.modeCombo)

        layout.addLayout(form)

        # Import/Export buttons
        btnLayout = QVBoxLayout()
        self.exportBtn = QLineEdit()
        self.exportBtn.setPlaceholderText("Click to export settings...")
        self.exportBtn.setReadOnly(True)
        self.exportBtn.mousePressEvent = lambda a0: self.exportSettings()
        btnLayout.addWidget(QLabel("Export:"))
        btnLayout.addWidget(self.exportBtn)

        self.importBtn = QLineEdit()
        self.importBtn.setPlaceholderText("Click to import settings...")
        self.importBtn.setReadOnly(True)
        self.importBtn.mousePressEvent = lambda a0: self.importSettings()
        btnLayout.addWidget(self.importBtn)

        layout.addLayout(btnLayout)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def exportSettings(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Settings", "settings.json", "JSON (*.json)"
        )
        if path:
            self.settings.export_settings(path)
            self.exportBtn.setText(f"Exported to {path}")

    def importSettings(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "", "JSON (*.json)"
        )
        if path:
            if self.settings.import_settings(path):
                self.importBtn.setText("Settings imported! Restart to apply.")
            else:
                self.importBtn.setText("Import failed!")

    def accept(self):
        self.settings.set("editor", "fontSize", value=self.fontSizeSpin.value())
        self.settings.set("editor", "tabSize", value=self.tabSizeSpin.value())
        self.settings.set("editor", "wordWrap", value=self.wordWrapCheck.isChecked())
        self.settings.set(
            "appearance", "useSystemFont", value=self.systemFontCheck.isChecked()
        )
        self.settings.set("mode", value=self.modeCombo.currentText())
        self.settings.save()
        super().accept()


# Main window entry point
if __name__ == "__main__":
    from window import MainWindow

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    App = QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(App.exec())
