# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt for more information.

# Main window for the Custom IDE.

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

# Fix import path and add missing functions
from languageSupport.syntax import (
    create_highlighter,
    create_highlighter_by_name,
    get_all_languages,
)
from main import (
    ClickableLabel,
    CodeEditor,
    Settings,
    SettingsDialog,
    TerminalWidget,
    Version,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.BasePath = Path(__file__).parent
        self.CurrentFile = None
        self.CurrentEncoding = "UTF-8"

        # Load settings
        self.Settings = Settings(self.BasePath)
        self.Mode = self.Settings.detect_mode()

        # Font setup
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

        # Window settings
        self.setWindowTitle("Custom IDE")
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
        # Center editor
        self.Editor = CodeEditor()
        self.Editor.cursorPositionChanged.connect(self.UpdateStatus)

        # Status bar
        self.Status = QStatusBar()
        self.Status.setObjectName("mainStatusBar")
        self.setStatusBar(self.Status)

        # Permanent status bar widgets
        self.StatusLine = QLabel("Line 1")
        self.StatusCol = QLabel("Col 1")
        self.StatusLanguage = ClickableLabel("Plain text")
        self.StatusEncoding = ClickableLabel("UTF-8")
        self.StatusTotal = QLabel("Total 1")
        self.StatusMode = ClickableLabel(f"[{self.Mode.upper()}]")

        # Build language menu with categories
        self.LanguageMenu = QMenu(self)
        self._all_languages = sorted(get_all_languages())
        self._search_actions = []  # Track search result actions

        # Add search box at top
        self._lang_search_box = QLineEdit()
        self._lang_search_box.setPlaceholderText("Search languages...")
        self._lang_search_box.textChanged.connect(self._filter_language_menu)
        search_widget_action = QWidgetAction(self.LanguageMenu)
        search_widget_action.setDefaultWidget(self._lang_search_box)
        self.LanguageMenu.addAction(search_widget_action)

        # Separator after search
        self._search_separator = self.LanguageMenu.addSeparator()

        # Language categories
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
                "JavaScript (JSX)",
                "TypeScript (TSX)",
                "Vue",
                "Svelte",
                "Astro",
                "SCSS",
                "Sass",
                "Less",
                "PHP",
                "JSON",
                "JSON5",
                "XML",
                "SVG",
                "XHTML",
            ],
            "Systems": [
                "C",
                "C++",
                "C Header",
                "C++ Header",
                "Rust",
                "Go",
                "Zig",
                "Nim",
                "D",
                "Assembly",
                "Verilog",
                "SystemVerilog",
                "VHDL",
            ],
            "JVM": [
                "Java",
                "Kotlin",
                "Kotlin Script",
                "Scala",
                "Groovy",
                "Clojure",
            ],
            ".NET": [
                "C#",
                "F#",
                "F# Script",
            ],
            "Scripting": [
                "Python",
                "Ruby",
                "Perl",
                "Perl Module",
                "Lua",
                "PHP",
                "Bash",
                "Shell",
                "Zsh",
                "Fish",
                "PowerShell",
                "PowerShell Module",
                "Batch",
                "AWK",
                "Tcl",
                "Vim Script",
                "AppleScript",
            ],
            "Functional": [
                "Haskell",
                "Literate Haskell",
                "OCaml",
                "OCaml Interface",
                "F#",
                "F# Script",
                "Elixir",
                "Elixir Script",
                "Erlang",
                "Erlang Header",
                "Clojure",
                "ClojureScript",
                "Common Lisp",
                "Emacs Lisp",
                "Scheme",
                "Racket",
            ],
            "Data / Config": [
                "JSON",
                "JSON5",
                "YAML",
                "TOML",
                "XML",
                "INI",
                "Config",
                "Properties",
                "Environment",
                "EditorConfig",
            ],
            "Markup": [
                "Markdown",
                "reStructuredText",
                "LaTeX",
                "BibTeX",
                "HTML",
            ],
            "Mobile": [
                "Swift",
                "Objective-C",
                "Objective-C++",
                "Kotlin",
                "Dart",
                "Java",
            ],
            "Scientific": [
                "Python",
                "R",
                "Julia",
                "Fortran",
                "MATLAB",
            ],
            "Other": [
                "Ada",
                "COBOL",
                "Pascal",
                "Prolog",
                "Cython",
                "Makefile",
                "CMake",
                "Dockerfile",
                "Nginx",
                "Gradle",
                "Git Ignore",
                "Git Attributes",
                "QSS",
            ],
        }

        # Add "Plain Text" at top
        self.LanguageMenu.addAction(
            "Plain Text", lambda: self.SetLanguage("Plain Text")
        )
        self.LanguageMenu.addSeparator()

        # Get all available languages
        all_languages = set(get_all_languages())

        # Add categorized submenus
        for category, langs in language_categories.items():
            submenu = self.LanguageMenu.addMenu(category)
            # Filter to only languages that exist and sort them
            available = sorted(set(langs) & all_languages)
            for lang_name in available:
                submenu.addAction(lang_name, lambda l=lang_name: self.SetLanguage(l))

        # Add "All Languages" submenu with everything alphabetically
        self._all_langs_separator = self.LanguageMenu.addSeparator()
        self._all_langs_menu = self.LanguageMenu.addMenu("All Languages")
        for lang_name in sorted(all_languages):
            self._all_langs_menu.addAction(
                lang_name, lambda l=lang_name: self.SetLanguage(l)
            )

        # Store category menus for hiding during search
        self._category_menus = [
            self.LanguageMenu.actions()[i]
            for i in range(3, len(self.LanguageMenu.actions()) - 2)
            if self.LanguageMenu.actions()[i].menu() is not None
        ]
        self._plain_text_action = self.LanguageMenu.actions()[2]  # Plain Text action
        self._plain_text_separator = self.LanguageMenu.actions()[
            3
        ]  # Separator after Plain Text

        # Clear search when menu is shown
        self.LanguageMenu.aboutToShow.connect(self._on_language_menu_show)

        self.StatusLanguage.setMenu(self.LanguageMenu)

        # Continue with the rest of the UI
        self._build_remaining_ui()

    def _on_language_menu_show(self):
        # Reset search when menu opens.
        self._lang_search_box.clear()
        self._lang_search_box.setFocus()
        self._show_categories(True)
        self._clear_search_results()

    def _filter_language_menu(self, text):
        # Filter languages based on search text.
        self._clear_search_results()

        if not text.strip():
            self._show_categories(True)
            return

        # Hide categories when searching
        self._show_categories(False)

        # Filter languages
        filter_lower = text.lower()
        matches = [lang for lang in self._all_languages if filter_lower in lang.lower()]
        # Sort: starts with filter first, then alphabetically
        matches.sort(key=lambda x: (not x.lower().startswith(filter_lower), x.lower()))

        # Show up to 15 matches
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
        # Show or hide category submenus.
        self._plain_text_action.setVisible(show)
        self._plain_text_separator.setVisible(show)
        for action in self._category_menus:
            action.setVisible(show)
        self._all_langs_separator.setVisible(show)
        self._all_langs_menu.menuAction().setVisible(show)

    def _clear_search_results(self):
        # Remove search result actions.
        for action in self._search_actions:
            self.LanguageMenu.removeAction(action)
        self._search_actions.clear()

    def _build_remaining_ui(self):
        # Continue building UI after language menu setup.
        # Build encoding menu

        self.EncodingMenu = QMenu(self)
        encodings = ["UTF-8", "UTF-16", "ASCII", "ISO-8859-1", "Windows-1252"]
        for enc in encodings:
            self.EncodingMenu.addAction(enc, lambda e=enc: self.SetEncoding(e))
        self.StatusEncoding.setMenu(self.EncodingMenu)

        # Build mode menu
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

        # Terminal (disabled in safe mode)
        self.Terminal = TerminalWidget()
        if self.Mode == "safe":
            self.Terminal.setEnabled(False)
            self.Terminal.OutputArea.setPlainText("Terminal disabled in Safe Mode")

        # Splitters
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
        # Helper to add menu action with optional shortcut.
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

        # File menu
        FileMenu = Bar.addMenu("File")
        if FileMenu is not None:
            self.AddMenuAction(FileMenu, "New", self.NewFile, keybinds.get("newFile"))
            self.AddMenuAction(
                FileMenu, "Open File…", self.OpenFile, keybinds.get("openFile")
            )
            self.AddMenuAction(
                FileMenu, "Open Folder…", self.OpenFolder, keybinds.get("openFolder")
            )
            self.AddMenuAction(FileMenu, "Clear Explorer", self.ClearExplorer)

            # Recent files submenu
            recentFiles = self.Settings.get("recentFiles", default=[]) or []
            if recentFiles:
                FileMenu.addSeparator()
                RecentMenu = FileMenu.addMenu("Recent Files")
                if RecentMenu is not None:
                    for path in recentFiles[:5]:
                        if Path(path).exists():
                            self.AddMenuAction(
                                RecentMenu,
                                Path(path).name,
                                lambda p=path: self.LoadFile(p),
                            )

            FileMenu.addSeparator()
            self.AddMenuAction(FileMenu, "Save", self.SaveFile, keybinds.get("save"))
            self.AddMenuAction(
                FileMenu, "Save As…", self.SaveFileAs, keybinds.get("saveAs")
            )
            FileMenu.addSeparator()
            self.AddMenuAction(FileMenu, "Exit", self.close, keybinds.get("exit"))

        # Edit menu
        EditMenu = Bar.addMenu("Edit")
        if EditMenu is not None:
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

        # View menu
        ViewMenu = Bar.addMenu("View")
        if ViewMenu is not None:
            self.AddMenuAction(
                ViewMenu,
                "Toggle Sidebar",
                self.ToggleSidebar,
                keybinds.get("toggleSidebar"),
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

        # Tools menu
        ToolsMenu = Bar.addMenu("Tools")
        if ToolsMenu is not None:
            self.AddMenuAction(ToolsMenu, "Settings", self.OpenSettings)
            if self.Mode != "safe":
                self.AddMenuAction(ToolsMenu, "Terminal", self.OpenTerminal)
            self.AddMenuAction(ToolsMenu, "Style", self.OpenStyleOptions)

        # Help menu
        HelpMenu = Bar.addMenu("Help")
        if HelpMenu is not None:
            self.AddMenuAction(
                HelpMenu,
                "About",
                lambda: QMessageBox.about(
                    self,
                    "About",
                    f"Custom IDE v{Version}\nMode: {self.Mode.upper()}",
                ),
            )

    def ApplySettings(self):
        # Apply editor font size
        fontSize = int(self.Settings.get("editor", "fontSize", default=11) or 11)
        font = self.Editor.font()
        font.setPointSize(fontSize)
        self.Editor.setFont(font)

        # Apply word wrap
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
        self.setWindowTitle(f"{FolderObj.name} - Custom IDE")

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
            self.setWindowTitle(f"{Path(FilePath).name} - Custom IDE")

    def LoadFile(self, FilePath):
        FileObj = Path(FilePath).resolve()

        self.Editor.setPlainText(FileObj.read_text(encoding="utf-8"))

        self.CurrentFile = str(FileObj)
        self.CurrentEncoding = "UTF-8"
        self.Editor.setLanguage(str(FileObj))
        self.UpdateStatus()
        self.setWindowTitle(f"{FileObj.name} - Custom IDE")

        # Track recent file
        self.Settings.add_recent_file(str(FileObj))

        # File explorer sync
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
        # Manually set the editor language for syntax highlighting.
        if self.Editor.Highlighter:
            self.Editor.Highlighter.setDocument(None)

        self.Editor.Highlighter, self.Editor.Language = create_highlighter_by_name(
            self.Editor.document(), language
        )
        self.UpdateStatus()
        self.ShowStatusMessage(f"Language set to {language}")

    def SetEncoding(self, encoding):
        # Set the current file encoding.
        self.CurrentEncoding = encoding
        self.UpdateStatus()
        self.ShowStatusMessage(f"Encoding set to {encoding}")

    def SetMode(self, mode):
        # Change the IDE mode (requires restart to fully apply).
        self.Settings.set("mode", value=mode)
        self.Settings.save()
        self.Mode = mode
        self.StatusMode.setText(f"[{mode.upper()}]")

        # Update terminal state
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

    # Tool actions
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
        # Save window state
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
