# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt for more information.

import json
import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QProcess, QRect, QSize, Qt
from PyQt6.QtGui import QMouseEvent, QPainter, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
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

from languageSupport.syntax import create_completer, create_highlighter

AppName = "CoreFlow IDE"
Version = "2.1.0"


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


class Settings:
    def __init__(self, base_path):
        self.base_path = base_path
        self.settings_file = base_path / "settings.json"
        self.defaults_file = base_path / "defaults" / "settings.json"
        self.data = self.load()

    def load(self):
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
        self.data["recentFiles"] = recent[:10]
        self.save()

    def add_recent_folder(self, path):
        recent = self.data.get("recentFolders", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.data["recentFolders"] = recent[:5]
        self.save()

    def detect_mode(self):
        mode = self.data.get("mode", "full")
        if os.environ.get("IDE_SAFE_MODE"):
            return "safe"
        if os.environ.get("IDE_RESTRICTED_MODE"):
            return "restricted"
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


class LineNumberWidget(QWidget):
    def __init__(self, Editor):
        super().__init__(Editor)
        self.setObjectName("lineNumberArea")
        self.Editor = Editor

    def sizeHint(self):
        return QSize(self.Editor.LineNumberWidth(), 0)

    def paintEvent(self, a0):
        self.Editor.PaintLineNumbers(a0)


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()

        self.setObjectName("codeEditor")
        self.LineNumbers = LineNumberWidget(self)
        self.Highlighter = None
        self.Language = "Plain text"
        self.completer = None

        TabSpaceAmount = " " * 4
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(TabSpaceAmount))

        self.blockCountChanged.connect(self.UpdateLineNumberWidth)
        self.updateRequest.connect(self.UpdateLineNumbers)
        self.UpdateLineNumberWidth(0)

        self.setCompleter(create_completer("Plain Text"))

    def setCompleter(self, completer):
        if self.completer:
            try:
                self.completer.activated.disconnect()
            except:
                pass

        self.completer = completer
        if not self.completer:
            return

        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        if not self.completer or self.completer.widget() != self:
            return

        tc = self.textCursor()

        if (
            hasattr(self.completer, "snippets")
            and completion in self.completer.snippets
        ):
            snippet = self.completer.snippets[completion]
            tc.select(QTextCursor.SelectionType.WordUnderCursor)
            tc.removeSelectedText()
            tc.insertText(snippet)
        else:
            extra = len(completion) - len(self.completer.completionPrefix())
            tc.movePosition(QTextCursor.MoveOperation.Left)
            tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
            tc.insertText(completion[-extra:])

        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, e):
        # Handle popup keys
        if self.completer and self.completer.popup().isVisible():
            if e.key() in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Tab,
            ):
                e.ignore()
                return

        # Check for completion shortcut
        is_shortcut = (
            e.modifiers() == Qt.KeyboardModifier.ControlModifier
            and e.key() == Qt.Key.Key_Space
        )

        # Normal key handling
        if not is_shortcut:
            super().keyPressEvent(e)

        # Don't show completion if no completer
        if not self.completer:
            return

        # Get completion prefix
        completion_prefix = self.textUnderCursor()

        # Hide if conditions not met
        ctrl_or_shift = e.modifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        )
        has_modifier = (
            e.modifiers() != Qt.KeyboardModifier.NoModifier and not ctrl_or_shift
        )

        if not is_shortcut and (has_modifier or len(completion_prefix) < 2):
            self.completer.popup().hide()
            return

        # Update and show completer
        if completion_prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(completion_prefix)
            self.completer.popup().setCurrentIndex(
                self.completer.completionModel().index(0, 0)
            )

        # Position popup
        cr = self.cursorRect()
        cr.setWidth(
            self.completer.popup().sizeHintForColumn(0)
            + self.completer.popup().verticalScrollBar().sizeHint().width()
        )

        # Show above if there's room
        popup_height = self.completer.popup().sizeHint().height()
        if cr.top() > popup_height:
            cr.translate(0, -popup_height - cr.height())

        self.completer.complete(cr)

    def setLanguage(self, file_path):
        if self.Highlighter:
            self.Highlighter.setDocument(None)
        self.Highlighter, self.Language = create_highlighter(self.document(), file_path)

        new_completer = create_completer(self.Language)
        self.setCompleter(new_completer)

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


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

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

        self.modeCombo = QComboBox()
        self.modeCombo.addItems(["full", "restricted", "safe"])
        self.modeCombo.setCurrentText(settings.get("mode", default="full"))
        form.addRow("Mode:", self.modeCombo)

        layout.addLayout(form)

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
                self.importBtn.setText(
                    f"{AppName} Settings imported! Restart to apply."
                )
            else:
                self.importBtn.setText(f"{AppName} Import failed!")

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


if __name__ == "__main__":
    from window import MainWindow

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    App = QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(App.exec())
