# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt file for more information.
# This is an early access build, expect bugs and incomplete features.
# Version 1.2.0

#Start of main.py

print("APP STARTED AT", __import__('datetime').datetime.now().strftime("%H:%M:%S"))
import sys
import os
from PyQt6.QtCore import QSize, Qt, QRect, QFileSystemWatcher
from PyQt6.QtGui import QAction, QFontDatabase, QFont, QIcon, QPainter, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QPlainTextEdit,
    QWidget, QVBoxLayout, QStatusBar
)


# Resource Helper
def get_resource_path(*args):
    """
    Resolves paths relative to main.py.
    Example: get_resource_path("defaults", "mainAppIcon.png")
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, *args)


# Custom Editor Widgets
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setObjectName("lineNumberArea") # ID for QSS styling

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setObjectName("codeEditor") # ID for QSS styling
        
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        # Width logic: padding + character width (compatible with different Qt versions)
        fm = self.fontMetrics()
        if hasattr(fm, "horizontalAdvance"):
            char_width = fm.horizontalAdvance('9')
        else:
            # fallback for older Qt versions
            char_width = fm.boundingRect('9').width()
        space = 25 + char_width * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        
        # Read colors from QSS (Palette)
        bg_color = self.line_number_area.palette().color(QPalette.ColorRole.Window)
        text_color = self.line_number_area.palette().color(QPalette.ColorRole.WindowText)

        # 1. Fill Gutter Background
        painter.fillRect(event.rect(), bg_color)

        # 2. Draw Line Numbers
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setPen(text_color)
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, top, self.line_number_area.width() - 10, self.fontMetrics().height(),
                               Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


# Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom IDE")
        self.setMinimumSize(900, 600)
        
        self.setup_ui()
        self.load_resources()
        self.setup_watcher() # New call for live reload

    def setup_ui(self):
        # Toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setObjectName("mainToolbar") # ID for QSS styling
        self.addToolBar(toolbar)

        actions = ["File", "Edit", "View", "Tools", "Help"]
        for name in actions:
            action = QAction(name, self)
            toolbar.addAction(action)

        # Editor Setup
        self.editor = CodeEditor()
        self.editor.cursorPositionChanged.connect(self.update_status) # Update status on move
        
        # Status Bar Setup
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("mainStatusBar")
        self.setStatusBar(self.status_bar)

        # Central Widget
        container = QWidget()
        container.setObjectName("centralContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.editor)
        self.setCentralWidget(container)
        self.update_status()

    def update_status(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        total = self.editor.blockCount()
        self.status_bar.showMessage(f" Line: {line}  |  Col: {col}  |  Total: {total}")

    def load_resources(self):
        # 1. Load Icon
        icon_path = get_resource_path("defaults", "mainAppIcon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 2. Load Fonts
        # Note: We load them, but we assign them via QSS now!
        self.load_font_db("defaults/mainFonts/Inter-VariableFont_opsz,wght.ttf")
        self.load_font_db("defaults/mainFonts/RobotoMono-VariableFont_wght.ttf")

        # 3. Load QSS
        self.reload_stylesheet()

    def reload_stylesheet(self):
        qss_path = get_resource_path("style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            # Trigger gutter repaint to pick up potential color changes
            self.editor.line_number_area.update()
        else:
            print(f"Warning: {qss_path} not found.")

    def setup_watcher(self):
        """Sets up a watcher to monitor the QSS file for changes."""
        self.watcher = QFileSystemWatcher()
        qss_path = get_resource_path("style.qss")
        if os.path.exists(qss_path):
            self.watcher.addPath(qss_path)
            self.watcher.fileChanged.connect(self.reload_stylesheet)

    def load_font_db(self, rel_path):
        # Helper to register font so QSS can use the family name
        path = get_resource_path(*rel_path.split("/"))
        if os.path.exists(path):
            QFontDatabase.addApplicationFont(path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(lambda: print("APP CLOSED AT", __import__('datetime').datetime.now().strftime("%H:%M:%S")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

# End of main.py