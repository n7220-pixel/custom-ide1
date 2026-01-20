# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt for more information.

Version = "1.8.0"

# Imports
import sys
import os
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QRect, QRegularExpression, QFileSystemWatcher, QProcess
from PyQt6.QtGui import (
    QFont, QPainter, QSyntaxHighlighter,
    QTextCharFormat, QColor, QFileSystemModel,
    QFontDatabase, QIcon, QTextCursor
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit,
    QWidget, QStatusBar, QTreeView, QSplitter,
    QFileDialog, QMessageBox, QVBoxLayout, QLineEdit
)

# Syntax highlighting
from languageSupport.syntax import create_highlighter

# Line number area
class LineNumberWidget(QWidget):
    def __init__(self, Editor):
        super().__init__(Editor)
        self.setObjectName("lineNumberArea")
        self.Editor = Editor

    def sizeHint(self):
        return QSize(self.Editor.LineNumberWidth(), 0)

    def paintEvent(self, Event):
        self.Editor.PaintLineNumbers(Event)

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
        if self.Highlighter:
            self.Highlighter.setDocument(None)

        self.Highlighter, self.Language = create_highlighter(
            self.document(),
            file_path
        )

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
                0, Rect.y(),
                self.LineNumbers.width(),
                Rect.height()
            )

    def resizeEvent(self, Event):
        super().resizeEvent(Event)
        Cr = self.contentsRect()
        self.LineNumbers.setGeometry(
            QRect(Cr.left(), Cr.top(),
                  self.LineNumberWidth(), Cr.height())
        )

    def PaintLineNumbers(self, Event):
        Painter = QPainter(self.LineNumbers)
        Painter.fillRect(
            Event.rect(),
            self.LineNumbers.palette().window()
        )
        Painter.setPen(
            self.LineNumbers.palette().text().color()
        )

        Block = self.firstVisibleBlock()
        Number = Block.blockNumber()
        Top = int(self.blockBoundingGeometry(Block).translated(self.contentOffset()).top())
        Bottom = Top + int(self.blockBoundingRect(Block).height())

        while Block.isValid() and Top <= Event.rect().bottom():
            if Block.isVisible() and Bottom >= Event.rect().top():
                Painter.drawText(
                    0,
                    Top,
                    self.LineNumbers.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(Number + 1)
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

# Main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.BasePath = Path(__file__).parent
        self.CurrentFile = None
        self.CurrentEncoding = "UTF-8"

        # Font setup
        QFontDatabase.addApplicationFont(
            str(self.BasePath / "defaults/mainFonts/Inter-VariableFont_opsz,wght.ttf")
        )
        QFontDatabase.addApplicationFont(
            str(self.BasePath / "defaults/mainFonts/RobotoMono-VariableFont_wght.ttf")
        )

        # Window settings
        self.setWindowTitle("Custom IDE")
        self.setMinimumSize(600, 400)
        self.setGeometry(100, 100, 1100, 800)
        self.setWindowIcon(
            QIcon(str(self.BasePath / "defaults/mainAppIcon.png"))
        )

        self.BuildUi()
        self.LoadStyles()
        self.SetupWatcher()

    # Ui building
    def BuildUi(self):
        # Center editor
        self.Editor = CodeEditor()
        self.Editor.cursorPositionChanged.connect(self.UpdateStatus)

        # Status bar
        self.Status = QStatusBar()
        self.Status.setObjectName("mainStatusBar")
        self.setStatusBar(self.Status)

        self.BuildMenuBar()

        # File explorer
        self.Model = QFileSystemModel()
        self.Model.setRootPath(os.path.expanduser("~")) 

        self.Tree = QTreeView()
        self.Tree.setObjectName("fileExplorer")
        self.Tree.setModel(self.Model)
        self.Tree.setHeaderHidden(True)
        self.Tree.setVisible(False)

        for Col in range(1, 4):
            self.Tree.setColumnHidden(Col, True)

        self.Tree.doubleClicked.connect(self.OpenFromTree)

        # Terminal
        self.Terminal = TerminalWidget()

        # Splitters
        # Sidebar + Editor
        self.HorizontalSplitter = QSplitter(Qt.Orientation.Horizontal)
        self.HorizontalSplitter.addWidget(self.Tree)
        self.HorizontalSplitter.addWidget(self.Editor)
        self.HorizontalSplitter.setStretchFactor(1, 1)
        self.HorizontalSplitter.setSizes([250, 850])

        # Top Section + Terminal
        self.VerticalSplitter = QSplitter(Qt.Orientation.Vertical)
        self.VerticalSplitter.addWidget(self.HorizontalSplitter)
        self.VerticalSplitter.addWidget(self.Terminal)
        self.VerticalSplitter.setStretchFactor(0, 1)
        self.VerticalSplitter.setSizes([600, 200])

        self.setCentralWidget(self.VerticalSplitter)
        self.UpdateStatus()

    # Menu bar
    def BuildMenuBar(self):
        Bar = self.menuBar()

        # File menu
        FileMenu = Bar.addMenu("File")
        FileMenu.addAction("New", self.NewFile)
        FileMenu.addAction("Open File…", self.OpenFile)
        FileMenu.addAction("Open Folder…", self.OpenFolder)
        FileMenu.addAction("Clear Explorer", self.ClearExplorer)
        FileMenu.addSeparator()
        FileMenu.addAction("Save", self.SaveFile)
        FileMenu.addAction("Save As…", self.SaveFileAs)
        FileMenu.addSeparator()
        FileMenu.addAction("Exit", self.close)

        # Edit menu
        EditMenu = Bar.addMenu("Edit")
        EditMenu.addAction("Undo", self.Editor.undo)
        EditMenu.addAction("Redo", self.Editor.redo)
        EditMenu.addSeparator()
        EditMenu.addAction("Cut", self.Editor.cut)
        EditMenu.addAction("Copy", self.Editor.copy)
        EditMenu.addAction("Paste", self.Editor.paste)

        # View menu
        ViewMenu = Bar.addMenu("View")
        ViewMenu.addAction("Toggle Sidebar", self.ToggleSidebar)
        ViewMenu.addSeparator()
        ViewMenu.addAction("Zoom In", self.ZoomIn)
        ViewMenu.addAction("Zoom Out", self.ZoomOut)
        ViewMenu.addAction("Reset Zoom", self.ResetZoom)

        # Tools menu
        ToolsMenu = Bar.addMenu("Tools")
        ToolsMenu.addAction("Settings", self.OpenSettings)
        ToolsMenu.addAction("Terminal", self.OpenTerminal)
        ToolsMenu.addAction("Style", self.OpenStyleOptions)

        # Help menu
        HelpMenu = Bar.addMenu("Help")
        HelpMenu.addAction("About", lambda: QMessageBox.about(self, "About", f"Custom IDE v{Version}"))

    

    # Styling
    def LoadStyles(self):
        StylePath = self.BasePath / "style.qss"
        if StylePath.exists():
            self.setStyleSheet(StylePath.read_text(encoding="utf-8"))

    def SetupWatcher(self):
        self.Watcher = QFileSystemWatcher()
        StylePath = self.BasePath / "style.qss"
        if StylePath.exists():
            self.Watcher.addPath(str(StylePath))
            self.Watcher.fileChanged.connect(self.LoadStyles)

    # File operations
    def NewFile(self):
        self.Editor.clear()
        self.CurrentFile = None
        self.setWindowTitle("New File - Custom IDE")

    def OpenFile(self):
        FilePath, _ = QFileDialog.getOpenFileName(self, "Open File")
        if FilePath:
            self.LoadFile(FilePath)

    def OpenFolder(self):
        Folder = QFileDialog.getExistingDirectory(self, "Open Folder", str(self.BasePath))
        if not Folder:
            return

        FolderObj = Path(Folder).resolve()
        
        # Standard IDE behavior: Set the selected folder as the root of the tree
        self.Model.setRootPath(str(FolderObj))
        self.Tree.setRootIndex(self.Model.index(str(FolderObj)))

        self.Tree.setVisible(True)
        self.setWindowTitle(f"{FolderObj.name} - Custom IDE")

    def ClearExplorer(self):
        # Reset the model root and hide the tree view
        self.Model.setRootPath("")
        self.Tree.setRootIndex(self.Model.index(""))
        self.Tree.setVisible(False)
        self.Status.showMessage("Explorer Cleared", 2000)

    def SaveFile(self):
        if not self.CurrentFile:
            self.SaveFileAs()
            return
        Path(self.CurrentFile).write_text(self.Editor.toPlainText(), encoding="utf-8")
        self.Status.showMessage("Saved", 2000)

    def SaveFileAs(self):
        FilePath, _ = QFileDialog.getSaveFileName(self, "Save File As")
        if FilePath:
            self.CurrentFile = FilePath
            self.SaveFile()
            self.setWindowTitle(f"{Path(FilePath).name} - Custom IDE")

    def LoadFile(self, FilePath):
        FileObj = Path(FilePath).resolve()

        self.Editor.setPlainText(
            FileObj.read_text(encoding="utf-8")
        )

        self.CurrentFile = str(FileObj)
        self.CurrentEncoding = "UTF-8"
        self.Editor.setLanguage(str(FileObj))
        self.UpdateStatus()
        self.setWindowTitle(f"{FileObj.name} - Custom IDE")

        # -------- FILE EXPLORER SYNC --------
        CurrentRoot = self.Model.rootPath()
        if not CurrentRoot or not self.CurrentFile.startswith(CurrentRoot):
            Parent = str(FileObj.parent)
            self.Model.setRootPath(Parent)
            self.Tree.setRootIndex(self.Model.index(Parent))
        
        FileIndex = self.Model.index(str(FileObj))
        self.Tree.setCurrentIndex(FileIndex)
        self.Tree.scrollTo(FileIndex)
        self.Tree.setVisible(True)


    def OpenFromTree(self, Index):
        FilePath = self.Model.filePath(Index)
        if os.path.isfile(FilePath):
            self.LoadFile(FilePath)

    # View actions
    def ToggleSidebar(self):
        self.Tree.setVisible(not self.Tree.isVisible())

    def ZoomIn(self):
        Font = self.Editor.font()
        Font.setPointSize(Font.pointSize() + 1)
        self.Editor.setFont(Font)

    def ZoomOut(self):
        Font = self.Editor.font()
        Font.setPointSize(max(6, Font.pointSize() - 1))
        self.Editor.setFont(Font)

    def ResetZoom(self):
        Font = self.Editor.font()
        Font.setPointSize(11)
        self.Editor.setFont(Font)

    def UpdateStatus(self):
        Cursor = self.Editor.textCursor()
        self.Status.showMessage(
            f"Line {Cursor.blockNumber()+1} | "
            f"Col {Cursor.columnNumber()+1} | "
            f"{self.Editor.Language} | "
            f"{self.CurrentEncoding} | "
            f"Total {self.Editor.blockCount()}"
        )

    # Tool actions
    def OpenSettings(self):
        QMessageBox.information(self, "Settings", "Settings logic not yet implemented.")

    def OpenTerminal(self):
        Visible = self.Terminal.isVisible()
        self.Terminal.setVisible(not Visible)
        if not Visible:
            self.Terminal.InputArea.setFocus()

    def OpenStyleOptions(self):
        StylePath = self.BasePath / "style.qss"
        if StylePath.exists():
            self.LoadFile(StylePath)
            self.Status.showMessage("Opened Style Configuration", 2000)
        else:
            QMessageBox.warning(self, "Style", "style.qss file not found!")

# Entry point
if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    App = QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(App.exec())