# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# Version 1.6.2

Version = "1.6.2"

# ---------------- Imports ----------------
import sys
import os
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QRect, QRegularExpression, QFileSystemWatcher
from PyQt6.QtGui import (
    QFont, QPainter, QSyntaxHighlighter,
    QTextCharFormat, QColor, QFileSystemModel,
    QFontDatabase, QIcon
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit,
    QWidget, QStatusBar, QTreeView, QSplitter,
    QFileDialog, QMessageBox
)

# ---------------- Syntax Highlighting ----------------

class PythonSyntax(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        Keyword = QTextCharFormat()
        Keyword.setForeground(QColor("#569cd6"))
        Keyword.setFontWeight(QFont.Weight.Bold)

        Function = QTextCharFormat()
        Function.setForeground(QColor("#dcdcaa"))

        String = QTextCharFormat()
        String.setForeground(QColor("#ce9178"))

        Comment = QTextCharFormat()
        Comment.setForeground(QColor("#6a9955"))

        Keywords = [
            "False","None","True","and","as","assert","break","class",
            "continue","def","del","elif","else","except","finally",
            "for","from","global","if","import","in","is","lambda",
            "nonlocal","not","or","pass","raise","return","try",
            "while","with","yield"
        ]

        self.Rules = (
            [(QRegularExpression(fr"\b{k}\b"), Keyword) for k in Keywords] + [
                (QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\()"), Function),
                (QRegularExpression(r"'[^']*'|\"[^\"]*\""), String),
                (QRegularExpression(r"#.*"), Comment),
            ]
        )

    def highlightBlock(self, text):
        for Pattern, Format in self.Rules:
            Iterator = Pattern.globalMatch(text)
            while Iterator.hasNext():
                Match = Iterator.next()
                self.setFormat(
                    Match.capturedStart(),
                    Match.capturedLength(),
                    Format
                )

# ---------------- Line Numbers ----------------

class LineNumberWidget(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.setObjectName("lineNumberArea")
        self.Editor = editor

    def sizeHint(self):
        return QSize(self.Editor.lineNumberWidth(), 0)

    def paintEvent(self, event):
        self.Editor.paintLineNumbers(event)

# ---------------- Code Editor ----------------

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()

        self.setObjectName("codeEditor")
        self.LineNumbers = LineNumberWidget(self)
        self.Highlighter = PythonSyntax(self.document())

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.blockCountChanged.connect(self.updateLineNumberWidth)
        self.updateRequest.connect(self.updateLineNumbers)

        self.updateLineNumberWidth(0)

    def lineNumberWidth(self):
        digits = len(str(max(1, self.blockCount())))
        return 35 + self.fontMetrics().horizontalAdvance("9") * digits

    def updateLineNumberWidth(self, _):
        self.setViewportMargins(self.lineNumberWidth(), 0, 0, 0)

    def updateLineNumbers(self, rect, dy):
        if dy:
            self.LineNumbers.scroll(0, dy)
        else:
            self.LineNumbers.update(
                0, rect.y(),
                self.LineNumbers.width(),
                rect.height()
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.LineNumbers.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.lineNumberWidth(), cr.height())
        )

    def paintLineNumbers(self, event):
        painter = QPainter(self.LineNumbers)
        painter.fillRect(
            event.rect(),
            self.LineNumbers.palette().window()
        )
        painter.setPen(
            self.LineNumbers.palette().text().color()
        )

        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self.LineNumbers.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1)
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            number += 1

# ---------------- Main Window ----------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.BasePath = Path(__file__).parent
        self.CurrentFile = None

        # Fonts
        QFontDatabase.addApplicationFont(
            str(self.BasePath / "defaults/mainFonts/Inter-VariableFont_opsz,wght.ttf")
        )
        QFontDatabase.addApplicationFont(
            str(self.BasePath / "defaults/mainFonts/RobotoMono-VariableFont_wght.ttf")
        )

        # Window
        self.setWindowTitle("Custom IDE")
        self.setMinimumSize(400, 200)
        self.setGeometry(100,100,1100,700)
        self.setWindowIcon(
            QIcon(str(self.BasePath / "defaults/mainAppIcon.png"))
        )

        self.buildUi()
        self.loadStyles()
        self.setupWatcher()

    # -------- UI --------

    def buildUi(self):
        self.Editor = CodeEditor()
        self.Editor.cursorPositionChanged.connect(self.updateStatus)

        self.Status = QStatusBar()
        self.Status.setObjectName("mainStatusBar")
        self.setStatusBar(self.Status)

        self.buildMenuBar()

        # File model starts EMPTY
        self.Model = QFileSystemModel()
        self.Model.setRootPath("")

        self.Tree = QTreeView()
        self.Tree.setObjectName("fileExplorer")
        self.Tree.setModel(self.Model)
        self.Tree.setRootIndex(self.Model.index(""))
        self.Tree.setHeaderHidden(True)
        self.Tree.setVisible(False)

        for col in range(1, 4):
            self.Tree.setColumnHidden(col, True)

        self.Tree.doubleClicked.connect(self.openFromTree)

        Splitter = QSplitter(Qt.Orientation.Horizontal)
        Splitter.addWidget(self.Tree)
        Splitter.addWidget(self.Editor)
        Splitter.setStretchFactor(1, 1)
        Splitter.setSizes([250, 850])

        self.setCentralWidget(Splitter)
        self.updateStatus()

    # -------- Menu Bar --------

    def buildMenuBar(self):
        Bar = self.menuBar()

        FileMenu = Bar.addMenu("File")
        FileMenu.addAction("New", self.newFile)
        FileMenu.addAction("Open File…", self.openFile)
        FileMenu.addAction("Open Folder…", self.openFolder)
        FileMenu.addSeparator()
        FileMenu.addAction("Save", self.saveFile)
        FileMenu.addAction("Save As…", self.saveFileAs)
        FileMenu.addSeparator()
        FileMenu.addAction("Exit", self.close)

        EditMenu = Bar.addMenu("Edit")
        EditMenu.addAction("Undo", self.Editor.undo)
        EditMenu.addAction("Redo", self.Editor.redo)
        EditMenu.addSeparator()
        EditMenu.addAction("Cut", self.Editor.cut)
        EditMenu.addAction("Copy", self.Editor.copy)
        EditMenu.addAction("Paste", self.Editor.paste)

        ViewMenu = Bar.addMenu("View")
        ViewMenu.addAction("Toggle Sidebar", self.toggleSidebar)
        ViewMenu.addSeparator()
        ViewMenu.addAction("Zoom In", self.zoomIn)
        ViewMenu.addAction("Zoom Out", self.zoomOut)
        ViewMenu.addAction("Reset Zoom", self.resetZoom)

        HelpMenu = Bar.addMenu("Help")
        HelpMenu.addAction(
            "About",
            lambda: QMessageBox.about(
                self, "About", f"Custom IDE v{Version}"
            )
        )

    # -------- Styling --------

    def loadStyles(self):
        path = self.BasePath / "style.qss"
        if path.exists():
            self.setStyleSheet(path.read_text(encoding="utf-8"))

    def setupWatcher(self):
        self.Watcher = QFileSystemWatcher()
        path = self.BasePath / "style.qss"
        if path.exists():
            self.Watcher.addPath(str(path))
            self.Watcher.fileChanged.connect(self.loadStyles)

    # -------- File Ops --------

    def newFile(self):
        self.Editor.clear()
        self.CurrentFile = None
        self.setWindowTitle("New File - Custom IDE")

    def openFile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self.loadFile(path)

    def openFolder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Open Folder", str(self.BasePath)
        )
        if not folder:
            return

        folder = Path(folder)
        self.Model.setRootPath(str(folder))
        self.Tree.setRootIndex(self.Model.index(str(folder)))
        self.Tree.setVisible(True)
        self.setWindowTitle(f"{folder.name} - Custom IDE")

    def saveFile(self):
        if not self.CurrentFile:
            self.saveFileAs()
            return

        Path(self.CurrentFile).write_text(
            self.Editor.toPlainText(), encoding="utf-8"
        )
        self.Status.showMessage("Saved", 2000)

    def saveFileAs(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File As")
        if path:
            self.CurrentFile = path
            self.saveFile()
            self.setWindowTitle(f"{Path(path).name} - Custom IDE")

    def loadFile(self, path):
        self.Editor.setPlainText(
            Path(path).read_text(encoding="utf-8")
        )
        self.CurrentFile = path
        self.setWindowTitle(f"{Path(path).name} - Custom IDE")

    def openFromTree(self, index):
        path = self.Model.filePath(index)
        if os.path.isfile(path):
            self.loadFile(path)

    # -------- View --------

    def toggleSidebar(self):
        self.Tree.setVisible(not self.Tree.isVisible())

    def zoomIn(self):
        f = self.Editor.font()
        f.setPointSize(f.pointSize() + 1)
        self.Editor.setFont(f)

    def zoomOut(self):
        f = self.Editor.font()
        f.setPointSize(max(6, f.pointSize() - 1))
        self.Editor.setFont(f)

    def resetZoom(self):
        f = self.Editor.font()
        f.setPointSize(11)
        self.Editor.setFont(f)

    def updateStatus(self):
        c = self.Editor.textCursor()
        self.Status.showMessage(
            f"Line {c.blockNumber()+1} | "
            f"Col {c.columnNumber()+1} | "
            f"Total {self.Editor.blockCount()}"
        )

# ---------------- Entry ----------------

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
