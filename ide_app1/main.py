# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT

# Imports
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import QProcess, QRect, QSize, Qt
from PyQt6.QtGui import (
    QFont,
    QFontDatabase,
    QMouseEvent,
    QPainter,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Language support handling
try:
    from languageSupport.syntax import create_completer, create_highlighter
except ImportError:
    print("Warning: Language support module not found. Defaulting to Plain Text.")

    def create_highlighter(doc, path):
        return None, "Plain Text"

    def create_completer(lang):
        return None


# App info
AppName = "CoreFlow IDE"
Version = "2.1.2"  # Unreleased build
Website = "https://example.com"
Author = "n7220-pixel"

# Centralized Defaults
DEFAULT_SETTINGS = {
    "version": Version,
    "mode": "full",
    "editor": {
        "fontSize": 11,
        "tabSize": 4,
        "wordWrap": False,
        "fontFamily": "Consolas",  # Fallback font
    },
    "terminal": {
        "fontSize": 10,
        "fontFamily": "Consolas",
        "shell_windows": "cmd.exe",
        "shell_unix": "/bin/bash",
    },
    "appearance": {"theme": "dark", "useSystemFont": False},
    "recentFiles": [],
    "recentFolders": [],
    "window": {
        "width": 1100,
        "height": 800,
        "sidebarWidth": 250,
        "terminalHeight": 200,
    },
}


# Monospace font checker
def get_monospace_fonts() -> list[str]:
    db = QFontDatabase()
    return db.families(QFontDatabase.SystemFont.FixedFont)


# Clickable label
class ClickableLabel(QLabel):
    def __init__(self, text: str = "", parent: Optional[QLabel] = None):
        super().__init__(text, parent)
        self.menu = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setMenu(self, menu):
        self.menu = menu

    def mousePressEvent(self, ev: Optional[QMouseEvent]) -> None:
        if ev and self.menu and ev.button() == Qt.MouseButton.LeftButton:
            self.menu.exec(self.mapToGlobal(ev.position().toPoint()))
        super().mousePressEvent(ev)


# Settings Manager
class Settings:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.settings_file = base_path / "settings.json"
        self.defaults_file = base_path / "defaults" / "settings.json"
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        # Priority: User Settings > Default File > Hardcoded Defaults
        candidates = [self.settings_file, self.defaults_file]

        for path in candidates:
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        merged = DEFAULT_SETTINGS.copy()
                        self._recursive_update(merged, data)
                        return merged
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Error loading settings from {path}: {e}")

        return DEFAULT_SETTINGS.copy()

    def _recursive_update(self, base_dict, update_dict):
        """Recursively updates base_dict with update_dict."""
        for key, value in update_dict.items():
            if (
                isinstance(value, dict)
                and key in base_dict
                and isinstance(base_dict[key], dict)
            ):
                self._recursive_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def save(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            self.settings_file.write_text(
                json.dumps(self.data, indent=4), encoding="utf-8"
            )
        except OSError as e:
            print(f"Failed to save settings: {e}")

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
            data = data.setdefault(key, {})
        data[keys[-1]] = value

    def add_recent_file(self, file_path: str):
        recent = self.data.get("recentFiles", [])
        if file_path in recent:
            recent.remove(file_path)
        recent.insert(0, file_path)
        self.data["recentFiles"] = recent[:10]
        self.save()

    def add_recent_folder(self, folder_path: str):
        recent = self.data.get("recentFolders", [])
        if folder_path in recent:
            recent.remove(folder_path)
        recent.insert(0, folder_path)
        self.data["recentFolders"] = recent[:10]
        self.save()

    def detect_mode(self):
        mode = self.data.get("mode", "full")

        if os.environ.get("IDE_SAFE_MODE"):
            return "safe"

        if os.environ.get("IDE_RESTRICTED_MODE"):
            return "restricted"

        try:
            test_file = self.base_path / ".perm_check"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError):
            return "safe"

        return mode


# Settings dialog
class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(f"{AppName} Settings")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Editor settings
        self.fontSize = QSpinBox()
        self.fontSize.setRange(6, 72)
        self.fontSize.setValue(settings.get("editor", "fontSize", default=11))
        form.addRow("Font Size:", self.fontSize)

        self.tabSize = QSpinBox()
        self.tabSize.setRange(1, 8)
        self.tabSize.setValue(settings.get("editor", "tabSize", default=4))
        form.addRow("Tab Size:", self.tabSize)

        self.wordWrap = QCheckBox()
        self.wordWrap.setChecked(settings.get("editor", "wordWrap", default=False))
        form.addRow("Word Wrap:", self.wordWrap)

        # Dynamic font loading
        self.fontFamily = QComboBox()
        available_fonts = get_monospace_fonts()
        if not available_fonts:
            available_fonts = [
                "Courier New",
                "Consolas",
                "Monospace",
            ]  # Emergency fallback

        self.fontFamily.addItems(available_fonts)

        current_font = settings.get("editor", "fontFamily", default="Consolas")
        index = self.fontFamily.findText(current_font, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.fontFamily.setCurrentIndex(index)
        elif available_fonts:
            self.fontFamily.setCurrentIndex(0)

        form.addRow("Editor Font:", self.fontFamily)

        # Appearance settings
        self.useSystemFont = QCheckBox()
        self.useSystemFont.setChecked(
            settings.get("appearance", "useSystemFont", default=False)
        )
        form.addRow("Use System UI Font:", self.useSystemFont)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.settings.set("editor", "fontSize", value=self.fontSize.value())
        self.settings.set("editor", "tabSize", value=self.tabSize.value())
        self.settings.set("editor", "wordWrap", value=self.wordWrap.isChecked())
        self.settings.set("editor", "fontFamily", value=self.fontFamily.currentText())
        self.settings.set(
            "appearance", "useSystemFont", value=self.useSystemFont.isChecked()
        )
        self.settings.save()
        super().accept()


# Line number area
class LineNumberWidget(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberWidth(), 0)

    def paintEvent(self, event):
        self.editor.paintLineNumbers(event)


# Code editor
class CodeEditor(QPlainTextEdit):
    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()

        self.settings = settings
        self.lineNumbers = LineNumberWidget(self)
        self.Highlighter = None
        self.Language = "Plain Text"
        self.completer: Optional[QCompleter] = None

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.applyEditorSettings()

        self.blockCountChanged.connect(self.updateLineNumberWidth)
        self.updateRequest.connect(self.updateLineNumbers)
        self.updateLineNumberWidth(0)

        self.setCompleter(create_completer("Plain Text"))

    def applyEditorSettings(self):
        defaults = DEFAULT_SETTINGS["editor"]

        font_family = defaults["fontFamily"]
        font_size = defaults["fontSize"]
        tab_size = defaults["tabSize"]
        word_wrap = defaults["wordWrap"]

        if self.settings:
            font_family = self.settings.get("editor", "fontFamily", default=font_family)
            font_size = self.settings.get("editor", "fontSize", default=font_size)
            tab_size = self.settings.get("editor", "tabSize", default=tab_size)
            word_wrap = self.settings.get("editor", "wordWrap", default=word_wrap)

        font = QFont(font_family)
        font.setPointSize(font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.updateTabStops(tab_size)

        if word_wrap:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def updateTabStops(self, tab_size: int):
        fm = self.fontMetrics()
        space_width = fm.horizontalAdvance(" ")
        self.setTabStopDistance(space_width * tab_size)

    def setCompleter(self, completer):
        if self.completer:
            try:
                self.completer.activated.disconnect()
            except (TypeError, RuntimeError):
                pass

        self.completer = completer
        if not completer:
            return

        completer.setWidget(self)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.activated.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def focusInEvent(self, e):
        if self.completer:
            self.completer.setWidget(self)
        super().focusInEvent(e)

    def keyPressEvent(self, e):
        if self.completer and self.completer.popup().isVisible():
            if e.key() in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab,
            ):
                e.ignore()
                return

        super().keyPressEvent(e)

        if self.completer:
            ctrl_space = (
                e.modifiers() == Qt.KeyboardModifier.ControlModifier
                and e.key() == Qt.Key.Key_Space
            )
            if ctrl_space:
                pass

            # Basic completion trigger logic would go here
            # For now relying on Syntax module to provide a configured completer

    def setLanguage(self, file_path):
        if self.Highlighter:
            self.Highlighter.setDocument(None)

        self.Highlighter, self.Language = create_highlighter(self.document(), file_path)
        self.setCompleter(create_completer(self.Language))

    def lineNumberWidth(self):
        digits = len(str(max(1, self.blockCount())))
        space = self.fontMetrics().horizontalAdvance(" ")
        return (space * 4) + (self.fontMetrics().horizontalAdvance("9") * digits)

    def updateLineNumberWidth(self, _):
        self.setViewportMargins(self.lineNumberWidth(), 0, 0, 0)

    def updateLineNumbers(self, rect, dy):
        if dy:
            self.lineNumbers.scroll(0, dy)
        else:
            self.lineNumbers.update(
                0, rect.y(), self.lineNumbers.width(), rect.height()
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumbers.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberWidth(), cr.height())
        )

    def paintLineNumbers(self, event):
        painter = QPainter(self.lineNumbers)
        painter.fillRect(event.rect(), self.palette().window())

        painter.setPen(self.palette().mid().color())
        painter.drawLine(event.rect().topRight(), event.rect().bottomRight())

        painter.setPen(self.palette().text().color())

        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())

        height = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self.lineNumbers.width() - 4,
                    height,
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            number += 1


# Terminal widget
class TerminalWidget(QWidget):
    def __init__(self, parent=None, settings: Optional[Settings] = None):
        super().__init__(parent)
        self.settings = settings

        self.Process = QProcess(self)
        self.Process.readyReadStandardOutput.connect(self.handleStdout)
        self.Process.readyReadStandardError.connect(self.handleStderr)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.OutputArea = QPlainTextEdit(readOnly=True)
        term_font = QFont("Consolas", 10)
        term_font.setStyleHint(QFont.StyleHint.Monospace)
        self.OutputArea.setFont(term_font)

        self.InputArea = QLineEdit()
        self.InputArea.returnPressed.connect(self.sendCommand)
        self.InputArea.setPlaceholderText("Enter command...")

        layout.addWidget(self.OutputArea)
        layout.addWidget(self.InputArea)

        cwd = os.getcwd()
        self.OutputArea.appendPlainText(f"Terminal started in {cwd}\n")

    def sendCommand(self):
        cmd = self.InputArea.text().strip()
        if not cmd:
            return

        self.OutputArea.appendPlainText(f"$ {cmd}")

        shell = "cmd.exe"
        args = ["/c", cmd]

        if self.settings:
            if os.name == "nt":
                shell = self.settings.get(
                    "terminal", "shell_windows", default="cmd.exe"
                )
                args = ["/c", cmd]
            else:
                shell = self.settings.get("terminal", "shell_unix", default="/bin/bash")
                args = ["-c", cmd]
        elif os.name != "nt":
            shell = "/bin/bash"
            args = ["-c", cmd]

        self.Process.start(shell, args)
        self.InputArea.clear()

    def handleStdout(self):
        data = self.Process.readAllStandardOutput().data()
        self.OutputArea.appendPlainText(data.decode(errors="replace"))
        self.OutputArea.moveCursor(QTextCursor.MoveOperation.End)

    def handleStderr(self):
        data = self.Process.readAllStandardError().data()
        self.OutputArea.appendPlainText(data.decode(errors="replace"))
        self.OutputArea.moveCursor(QTextCursor.MoveOperation.End)


# Entry point
if __name__ == "__main__":
    # Ensure this runs only if window.py exists
    try:
        from window import MainWindow

        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

        app = QApplication(sys.argv)
        app.setApplicationName(AppName)
        app.setApplicationVersion(Version)

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except ImportError as e:
        print("CRITICAL ERROR: Could not import MainWindow.")
        print(f"Make sure 'window.py' is in the same directory. Details: {e}")

        if "QApplication" in locals():
            app = QApplication(sys.argv)
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(None, "Startup Error", f"Missing component: {e}")
