# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt for more information.

import os
from pathlib import Path

from PyQt6.QtCore import QFileSystemWatcher, Qt
from PyQt6.QtGui import (
    QAction,
    QFileSystemModel,
    QFontDatabase,
    QIcon,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QTreeView,
    QWidgetAction,
)

from languageSupport.syntax import (
    create_completer,
    create_highlighter,
    create_highlighter_by_name,
    get_all_languages,
)
from main import (
    AppName,
    ClickableLabel,
    CodeEditor,
    Settings,
    SettingsDialog,
    TerminalWidget,
    Version,
    Website,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.BasePath = Path(__file__).parent
        self.CurrentFile = None
        self.CurrentEncoding = "UTF-8"

        self.Settings = Settings(self.BasePath)
        self.Mode = self.Settings.detect_mode()

        if not self.Settings.get("appearance", "useSystemFont", default=False):
            QFontDatabase.addApplicationFont(
                str(
                    self.BasePath
                    / "defaults/mainFonts/Inter-VariableFont_opsz,wght.ttf"
                )
            )
            QFontDatabase.addApplicationFont(
                str(
                    self.BasePath
                    / "defaults/mainFonts/RobotoMono-VariableFont_wght.ttf"
                )
            )

        self.setWindowTitle(AppName)
        self.setMinimumSize(600, 400)
        winSettings = self.Settings.get("window", default={}) or {}
        self.setGeometry(
            100,
            100,
            winSettings.get("width", 1100),
            winSettings.get("height", 800),
        )
        self.setWindowIcon(QIcon(str(self.BasePath / "defaults/mainAppIcon.png")))

        self.BuildUi()
        self.LoadStyles()
        self.SetupWatcher()
        self.ApplySettings()

    def BuildUi(self):
        self.Editor = CodeEditor()
        self.Editor.cursorPositionChanged.connect(self.UpdateStatus)

        self.Status = QStatusBar()
        self.Status.setObjectName("mainStatusBar")
        self.setStatusBar(self.Status)

        self.StatusLine = QLabel("Line 1")
        self.StatusCol = QLabel("Col 1")
        self.StatusLanguage = ClickableLabel("Plain text")
        self.StatusEncoding = ClickableLabel("UTF-8")
        self.StatusTotal = QLabel("Total 1")
        self.StatusMode = ClickableLabel(f"[{self.Mode.upper()}]")

        self.LanguageMenu = QMenu(self)
        self._all_languages = sorted(get_all_languages())
        self._search_actions = []

        self._lang_search_box = QLineEdit()
        self._lang_search_box.setPlaceholderText("Search languages...")
        self._lang_search_box.textChanged.connect(self._filter_language_menu)
        search_widget_action = QWidgetAction(self.LanguageMenu)
        search_widget_action.setDefaultWidget(self._lang_search_box)
        self.LanguageMenu.addAction(search_widget_action)

        self._search_separator = self.LanguageMenu.addSeparator()

        language_categories = {
            "Popular": [
                "Python",
                "JavaScript",
                "TypeScript",
                "HTML",
                "CSS",
                "JSON",
                "Markdown",
                "SQL",
                "Bash",
                "C",
                "C++",
                "Java",
                "Go",
                "Rust",
            ],
            "Web": [
                "HTML",
                "CSS",
                "JavaScript",
                "TypeScript",
                "React (JSX/TSX)",
                "Vue",
                "Svelte",
                "Astro",
                "SCSS",
                "Sass",
                "Less",
                "PHP",
                "JSON",
                "XML",
                "SVG",
            ],
            "Systems": [
                "C",
                "C++",
                "Rust",
                "Go",
                "Zig",
                "Nim",
                "D",
                "Assembly",
                "Verilog",
                "VHDL",
            ],
            "JVM": ["Java", "Kotlin", "Scala", "Groovy", "Clojure"],
            ".NET": ["C#", "F#", "Visual Basic"],
            "Scripting": [
                "Python",
                "Ruby",
                "Perl",
                "Lua",
                "PHP",
                "Bash",
                "Shell",
                "PowerShell",
                "Batch",
                "AWK",
                "Tcl",
                "Vim Script",
            ],
            "Functional": [
                "Haskell",
                "OCaml",
                "F#",
                "Elixir",
                "Erlang",
                "Clojure",
                "Common Lisp",
                "Scheme",
                "Racket",
            ],
            "Data / Config": [
                "JSON",
                "YAML",
                "TOML",
                "XML",
                "INI",
                "Properties",
            ],
            "Markup": ["Markdown", "reStructuredText", "LaTeX", "HTML"],
            "Mobile": [
                "Swift",
                "Objective-C",
                "Kotlin",
                "Dart",
                "Java",
            ],
            "Scientific": ["Python", "R", "Julia", "Fortran", "MATLAB"],
            "Other": [
                "Makefile",
                "CMake",
                "Dockerfile",
                "Nginx",
                "Gradle",
                "Ada",
                "COBOL",
                "Pascal",
                "Prolog",
                "Cython",
                "QSS",
            ],
        }

        self.LanguageMenu.addAction(
            "Plain Text", lambda: self.SetLanguage("Plain Text")
        )
        self.LanguageMenu.addSeparator()

        # Build a set of all languages from the categories
        all_languages = set()
        for langs in language_categories.values():
            all_languages.update(langs)

        for category, langs in language_categories.items():
            submenu = self.LanguageMenu.addMenu(category)
            available = sorted(set(langs) & all_languages)
            for lang_name in available:
                submenu.addAction(lang_name, lambda l=lang_name: self.SetLanguage(l))

        self._all_langs_separator = self.LanguageMenu.addSeparator()
        self._all_langs_menu = self.LanguageMenu.addMenu("All Languages")
        for lang_name in sorted(all_languages):
            self._all_langs_menu.addAction(
                lang_name, lambda l=lang_name: self.SetLanguage(l)
            )

        self._category_menus = [
            self.LanguageMenu.actions()[i]
            for i in range(3, len(self.LanguageMenu.actions()) - 2)
            if self.LanguageMenu.actions()[i].menu() is not None
        ]
        self._plain_text_action = self.LanguageMenu.actions()[2]
        self._plain_text_separator = self.LanguageMenu.actions()[3]

        self.LanguageMenu.aboutToShow.connect(self._on_language_menu_show)
        self.StatusLanguage.setMenu(self.LanguageMenu)

        self._build_remaining_ui()

    def _on_language_menu_show(self):
        self._lang_search_box.clear()
        self._lang_search_box.setFocus()
        self._show_categories(True)
        self._clear_search_results()

    def _filter_language_menu(self, text):
        self._clear_search_results()
        if not text.strip():
            self._show_categories(True)
            return

        self._show_categories(False)
        filter_lower = text.lower()
        matches = [lang for lang in self._all_languages if filter_lower in lang.lower()]
        matches.sort(key=lambda x: (not x.lower().startswith(filter_lower), x.lower()))

        for lang in matches[:15]:
            action = self.LanguageMenu.addAction(
                lang, lambda l=lang: self.SetLanguage(l)
            )
            self._search_actions.append(action)

        if not matches:
            no_match = self.LanguageMenu.addAction("No matches found")
            no_match.setEnabled(False)
            self._search_actions.append(no_match)

    def _show_categories(self, show):
        self._plain_text_action.setVisible(show)
        self._plain_text_separator.setVisible(show)
        for action in self._category_menus:
            action.setVisible(show)
        self._all_langs_separator.setVisible(show)
        self._all_langs_menu.menuAction().setVisible(show)

    def _clear_search_results(self):
        for action in self._search_actions:
            self.LanguageMenu.removeAction(action)
        self._search_actions.clear()

    def _build_remaining_ui(self):
        self.EncodingMenu = QMenu(self)
        encodings = ["UTF-8", "UTF-16", "ASCII", "ISO-8859-1", "Windows-1252"]
        for enc in encodings:
            self.EncodingMenu.addAction(enc, lambda e=enc: self.SetEncoding(e))
        self.StatusEncoding.setMenu(self.EncodingMenu)

        self.ModeMenu = QMenu(self)
        modes = ["full", "restricted", "safe"]
        for mode in modes:
            self.ModeMenu.addAction(mode.upper(), lambda m=mode: self.SetMode(m))
        self.StatusMode.setMenu(self.ModeMenu)

        self.Status.addPermanentWidget(self.StatusLine)
        self.Status.addPermanentWidget(self.StatusCol)
        self.Status.addPermanentWidget(self.StatusLanguage)
        self.Status.addPermanentWidget(self.StatusEncoding)
        self.Status.addPermanentWidget(self.StatusTotal)
        self.Status.addPermanentWidget(self.StatusMode)

        self.BuildMenuBar()

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

        self.Terminal = TerminalWidget()
        if self.Mode == "safe":
            self.Terminal.setEnabled(False)
            self.Terminal.OutputArea.setPlainText("Terminal disabled in Safe Mode")

        self.HorizontalSplitter = QSplitter(Qt.Orientation.Horizontal)
        self.HorizontalSplitter.addWidget(self.Tree)
        self.HorizontalSplitter.addWidget(self.Editor)
        self.HorizontalSplitter.setStretchFactor(1, 1)
        self.HorizontalSplitter.setSizes(
            [self.Settings.get("window", "sidebarWidth", default=250), 850]
        )

        self.VerticalSplitter = QSplitter(Qt.Orientation.Vertical)
        self.VerticalSplitter.addWidget(self.HorizontalSplitter)
        self.VerticalSplitter.addWidget(self.Terminal)
        self.VerticalSplitter.setStretchFactor(0, 1)
        self.VerticalSplitter.setSizes(
            [600, self.Settings.get("window", "terminalHeight", default=200)]
        )

        self.setCentralWidget(self.VerticalSplitter)
        self.UpdateStatus()

    def AddMenuAction(self, menu, text, slot, shortcut=None):
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)
        return action

    def BuildMenuBar(self):
        Bar = self.menuBar()
        if Bar is None:
            return

        keybinds = self.Settings.get("keybinds", default={}) or {}

        FileMenu = Bar.addMenu("File")
        if FileMenu:
            self.AddMenuAction(FileMenu, "New", self.NewFile, keybinds.get("newFile"))
            self.AddMenuAction(
                FileMenu, "Open File…", self.OpenFile, keybinds.get("openFile")
            )
            self.AddMenuAction(
                FileMenu, "Open Folder…", self.OpenFolder, keybinds.get("openFolder")
            )
            self.AddMenuAction(FileMenu, "Clear Explorer", self.ClearExplorer)

            recentFiles = self.Settings.get("recentFiles", default=[]) or []
            if recentFiles:
                FileMenu.addSeparator()
                RecentMenu = FileMenu.addMenu("Recent Files")
                for path in recentFiles[:5]:
                    if Path(path).exists():
                        self.AddMenuAction(
                            RecentMenu, Path(path).name, lambda p=path: self.LoadFile(p)
                        )

            FileMenu.addSeparator()
            self.AddMenuAction(FileMenu, "Save", self.SaveFile, keybinds.get("save"))
            self.AddMenuAction(
                FileMenu, "Save As…", self.SaveFileAs, keybinds.get("saveAs")
            )
            FileMenu.addSeparator()
            self.AddMenuAction(FileMenu, "Exit", self.close, keybinds.get("exit"))

        EditMenu = Bar.addMenu("Edit")
        if EditMenu:
            self.AddMenuAction(
                EditMenu, "Undo", self.Editor.undo, keybinds.get("undo", "Ctrl+Z")
            )
            self.AddMenuAction(
                EditMenu, "Redo", self.Editor.redo, keybinds.get("redo", "Ctrl+Shift+Z")
            )
            EditMenu.addSeparator()
            self.AddMenuAction(EditMenu, "Cut", self.Editor.cut, keybinds.get("cut"))
            self.AddMenuAction(EditMenu, "Copy", self.Editor.copy, keybinds.get("copy"))
            self.AddMenuAction(
                EditMenu, "Paste", self.Editor.paste, keybinds.get("paste")
            )

        ViewMenu = Bar.addMenu("View")
        if ViewMenu:
            self.AddMenuAction(
                ViewMenu,
                "Toggle Left Sidebar",
                self.ToggleLeftSidebar,
                keybinds.get("toggleLeftSidebar"),
            )
            self.AddMenuAction(
                ViewMenu,
                "Toggle Terminal",
                self.OpenTerminal,
                keybinds.get("toggleTerminal"),
            )
            ViewMenu.addSeparator()
            self.AddMenuAction(ViewMenu, "Zoom In", self.ZoomIn, keybinds.get("zoomIn"))
            self.AddMenuAction(
                ViewMenu, "Zoom Out", self.ZoomOut, keybinds.get("zoomOut")
            )
            self.AddMenuAction(
                ViewMenu, "Reset Zoom", self.ResetZoom, keybinds.get("resetZoom")
            )

        ToolsMenu = Bar.addMenu("Tools")
        if ToolsMenu:
            self.AddMenuAction(ToolsMenu, "Settings", self.OpenSettings)
            if self.Mode != "safe":
                self.AddMenuAction(ToolsMenu, "Terminal", self.OpenTerminal)
            self.AddMenuAction(ToolsMenu, "Style", self.OpenStyleOptions)

        HelpMenu = Bar.addMenu("Help")
        if HelpMenu:
            self.AddMenuAction(
                HelpMenu,
                "About",
                lambda: QMessageBox.about(
                    self, "About", f"{AppName} v{Version}\nMode: {self.Mode.upper()}"
                ),
            )
            self.AddMenuAction(
                HelpMenu,
                "Donate",
                lambda: QMessageBox.about(
                    self,
                    "Donate",
                    f"Donate to support the development of {AppName} at <a href='{Website}'>{Website}</a>.",
                ),
            )

    def ApplySettings(self):
        fontSize = int(self.Settings.get("editor", "fontSize", default=11) or 11)
        font = self.Editor.font()
        font.setPointSize(fontSize)
        self.Editor.setFont(font)
        if self.Settings.get("editor", "wordWrap", default=False):
            self.Editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.Editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def LoadStyles(self):
        StylePath = self.BasePath / "defaults" / "style.qss"
        if StylePath.exists():
            self.setStyleSheet(StylePath.read_text(encoding="utf-8"))

    def SetupWatcher(self):
        self.Watcher = QFileSystemWatcher()
        StylePath = self.BasePath / "defaults" / "style.qss"
        if StylePath.exists():
            self.Watcher.addPath(str(StylePath))
            self.Watcher.fileChanged.connect(self.LoadStyles)

    def NewFile(self):
        self.Editor.clear()
        self.CurrentFile = None
        self.setWindowTitle(f"New File - {AppName}")

    def OpenFile(self):
        FilePath, _ = QFileDialog.getOpenFileName(self, "Open File")
        if FilePath:
            self.LoadFile(FilePath)

    def OpenFolder(self):
        Folder = QFileDialog.getExistingDirectory(
            self, "Open Folder", str(self.BasePath)
        )
        if not Folder:
            return
        FolderObj = Path(Folder).resolve()
        self.Settings.add_recent_folder(str(FolderObj))
        self.Model.setRootPath(str(FolderObj))
        self.Tree.setRootIndex(self.Model.index(str(FolderObj)))
        self.Tree.setVisible(True)
        self.setWindowTitle(f"{FolderObj.name} - {AppName}")

    def ClearExplorer(self):
        self.Model.setRootPath("")
        self.Tree.setRootIndex(self.Model.index(""))
        self.Tree.setVisible(False)
        self.ShowStatusMessage("Explorer Cleared")

    def SaveFile(self):
        if not self.CurrentFile:
            self.SaveFileAs()
            return
        Path(self.CurrentFile).write_text(self.Editor.toPlainText(), encoding="utf-8")
        self.ShowStatusMessage("Saved")

    def SaveFileAs(self):
        FilePath, _ = QFileDialog.getSaveFileName(self, "Save File As")
        if FilePath:
            self.CurrentFile = FilePath
            self.SaveFile()
            self.setWindowTitle(f"{Path(FilePath).name} - {AppName}")

    def LoadFile(self, FilePath):
        FileObj = Path(FilePath).resolve()

        try:
            content = FileObj.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            QMessageBox.warning(
                self, "Error", f"Cannot open binary file:\n{FileObj.name}"
            )
            return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open file:\n{str(e)}")
            return

        self.Editor.setPlainText(content)
        self.CurrentFile = str(FileObj)
        self.CurrentEncoding = "UTF-8"
        self.Editor.setLanguage(str(FileObj))
        self.UpdateStatus()
        self.setWindowTitle(f"{FileObj.name} - {AppName}")
        self.Settings.add_recent_file(str(FileObj))

        CurrentRoot = self.Model.rootPath()

        is_within_root = False
        if CurrentRoot:
            try:
                FileObj.relative_to(CurrentRoot)
                is_within_root = True
            except ValueError:
                is_within_root = False

        if not CurrentRoot or not is_within_root:
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

    def ToggleLeftSidebar(self):
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
        Font.setPointSize(
            int(self.Settings.get("editor", "fontSize", default=11) or 11)
        )
        self.Editor.setFont(Font)

    def UpdateStatus(self):
        Cursor = self.Editor.textCursor()
        self.StatusLine.setText(f"Line {Cursor.blockNumber() + 1}")
        self.StatusCol.setText(f"Col {Cursor.columnNumber() + 1}")
        self.StatusLanguage.setText(self.Editor.Language)
        self.StatusEncoding.setText(self.CurrentEncoding)
        self.StatusTotal.setText(f"Total {self.Editor.blockCount()}")

    def SetLanguage(self, language):
        if self.Editor.Highlighter:
            self.Editor.Highlighter.setDocument(None)

        self.Editor.Highlighter, self.Editor.Language = create_highlighter_by_name(
            self.Editor.document(), language
        )

        new_completer = create_completer(language)
        self.Editor.setCompleter(new_completer)

        self.UpdateStatus()
        self.ShowStatusMessage(f"Language set to {language}")

    def SetEncoding(self, encoding):
        self.CurrentEncoding = encoding
        self.UpdateStatus()
        self.ShowStatusMessage(f"Encoding set to {encoding}")

    def SetMode(self, mode):
        self.Settings.set("mode", value=mode)
        self.Settings.save()
        self.Mode = mode
        self.StatusMode.setText(f"[{mode.upper()}]")
        if mode == "safe":
            self.Terminal.setEnabled(False)
            self.Terminal.OutputArea.setPlainText("Terminal disabled in Safe Mode")
        else:
            self.Terminal.setEnabled(True)
            if (
                self.Terminal.OutputArea.toPlainText()
                == "Terminal disabled in Safe Mode"
            ):
                self.Terminal.OutputArea.clear()
        self.ShowStatusMessage(
            f"Mode changed to {mode.upper()} (some features may require restart)"
        )

    def ShowStatusMessage(self, message):
        self.Status.showMessage(message, 5000)

    def OpenSettings(self):
        dialog = SettingsDialog(self.Settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.ApplySettings()
            self.ShowStatusMessage("Settings saved")

    def OpenTerminal(self):
        if self.Mode == "safe":
            self.ShowStatusMessage("Terminal disabled in Safe Mode")
            return
        Visible = self.Terminal.isVisible()
        self.Terminal.setVisible(not Visible)
        if not Visible:
            self.Terminal.InputArea.setFocus()

    def OpenStyleOptions(self):
        StylePath = self.BasePath / "defaults" / "style.qss"
        if StylePath.exists():
            self.LoadFile(StylePath)
            self.ShowStatusMessage("Opened Style Configuration")
        else:
            QMessageBox.warning(self, "Style", "style.qss file not found!")

    def closeEvent(self, a0):
        self.Settings.set("window", "width", value=self.width())
        self.Settings.set("window", "height", value=self.height())
        if hasattr(self, "HorizontalSplitter"):
            self.Settings.set(
                "window", "sidebarWidth", value=self.HorizontalSplitter.sizes()[0]
            )
        if hasattr(self, "VerticalSplitter"):
            self.Settings.set(
                "window", "terminalHeight", value=self.VerticalSplitter.sizes()[1]
            )
        self.Settings.save()
        super().closeEvent(a0)
