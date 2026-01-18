#Copyright (c) 2026 n7220-pixel
#SPDX-License-Identifier: MIT
#See LICENSE.txt for more information.

#This is an early access build
#Expect bugs and incomplete features

print("STARTING APP")

import sys
import os
import warnings

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction, QFontDatabase, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QToolBar,
    QTextEdit
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Custom IDE")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(600, 400)

        # Toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        for name in ["File", "Edit", "View", "Tools", "Help"]:
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, n=name: self.toolbar_button_clicked(n)
            )
            toolbar.addAction(action)

        # Text editor
        self.text_editor = QTextEdit()
        self.text_editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Explicit monospace font
        self.text_editor.setFont(QFont("Roboto Mono", 11))

        self.setCentralWidget(self.text_editor)

    def toolbar_button_clicked(self, name):
        print(f"{name} clicked")
        if name == "null":
            warnings.warn("A button without a name was requested!")
    
    def closeEvent(self, event):
        print("APP CLOSED")
        event.accept()



def load_font():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(
        base_dir,
        "Roboto_Mono",
        "RobotoMono-VariableFont_wght.ttf"
    )

    if not os.path.exists(font_path):
        print("Font file not found:", font_path)
        return

    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id == -1:
        print("Failed to load the font.")
        return

    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
    QApplication.setFont(QFont(font_family, 10))


def load_stylesheet(app):
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    try:
        with open(css_path, "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"Error: Could not find {css_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    load_font()
    load_stylesheet(app)

    window = MainWindow()
    window.show()

    print("SHOWING WINDOW")

    sys.exit(app.exec())

