# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt for more information.

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import QCompleter, QStyledItemDelegate

try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
    from pygments.token import Token
    from pygments.util import ClassNotFound

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

# Dark color scheme
TOKEN_COLORS = {
    Token.Keyword: ("#569cd6", True, False),
    Token.Keyword.Type: ("#4ec9b0", False, False),
    Token.Name: ("#d4d4d4", False, False),
    Token.Name.Function: ("#dcdcaa", False, False),
    Token.Name.Class: ("#4ec9b0", False, False),
    Token.Name.Builtin: ("#4ec9b0", False, False),
    Token.String: ("#ce9178", False, False),
    Token.String.Doc: ("#6a9955", False, True),
    Token.Number: ("#b5cea8", False, False),
    Token.Comment: ("#6a9955", False, True),
    Token.Comment.Multiline: ("#6a9955", False, True),
    Token.Operator: ("#d4d4d4", False, False),
    Token.Punctuation: ("#d4d4d4", False, False),
    Token.Text: ("#d4d4d4", False, False),
    Token.Error: ("#f44747", False, False),
}

DISPLAY_NAME_TO_ALIAS = {
    "C Header": "c",
    "C++ Header": "cpp",
    "JavaScript (JSX)": "jsx",
    "TypeScript (TSX)": "tsx",
    "Git Ignore": "gitignore",
    "QSS": "css",
}

# Language-specific autocomplete keywords and snippets
LANGUAGE_COMPLETIONS = {
    "Python": {
        "keywords": [
            "import",
            "from",
            "class",
            "def",
            "return",
            "if",
            "else",
            "elif",
            "while",
            "for",
            "try",
            "except",
            "finally",
            "with",
            "as",
            "assert",
            "global",
            "nonlocal",
            "lambda",
            "pass",
            "break",
            "continue",
            "raise",
            "yield",
            "async",
            "await",
            "and",
            "or",
            "not",
            "in",
            "is",
            "None",
            "True",
            "False",
            "self",
            "__init__",
            "__str__",
            "__repr__",
            "print",
            "len",
            "range",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
        ],
        "snippets": {
            "def": "def function_name():\n    pass",
            "class": "class ClassName:\n    def __init__(self):\n        pass",
            "if": "if condition:\n    pass",
            "for": "for item in iterable:\n    pass",
            "while": "while condition:\n    pass",
            "try": "try:\n    pass\nexcept Exception as e:\n    pass",
        },
    },
    "JavaScript": {
        "keywords": [
            "function",
            "const",
            "let",
            "var",
            "if",
            "else",
            "for",
            "while",
            "return",
            "class",
            "constructor",
            "async",
            "await",
            "try",
            "catch",
            "finally",
            "throw",
            "new",
            "this",
            "typeof",
            "instanceof",
            "null",
            "undefined",
            "true",
            "false",
            "export",
            "import",
            "from",
            "default",
            "console",
            "document",
            "window",
        ],
        "snippets": {
            "function": "function name() {\n    \n}",
            "const": "const name = value;",
            "class": "class ClassName {\n    constructor() {\n        \n    }\n}",
            "if": "if (condition) {\n    \n}",
            "for": "for (let i = 0; i < length; i++) {\n    \n}",
        },
    },
    "C": {
        "keywords": [
            "int",
            "char",
            "float",
            "double",
            "void",
            "if",
            "else",
            "for",
            "while",
            "return",
            "struct",
            "typedef",
            "enum",
            "sizeof",
            "const",
            "static",
            "extern",
            "switch",
            "case",
            "break",
            "continue",
            "do",
            "printf",
            "scanf",
            "malloc",
            "free",
        ],
        "snippets": {
            "for": "for (int i = 0; i < n; i++) {\n    \n}",
            "if": "if (condition) {\n    \n}",
            "struct": "struct name {\n    \n};",
        },
    },
}


class CompletionDelegate(QStyledItemDelegate):
    def __init__(self, snippets, parent=None):
        super().__init__(parent)
        self.snippets = snippets

    def paint(self, painter, option, index):
        painter.save()

        completion = index.data(Qt.ItemDataRole.DisplayRole)

        # Fill background
        if option.state & self.State.State_Selected:
            painter.fillRect(option.rect, QColor("#094771"))
        elif option.state & self.State.State_MouseOver:
            painter.fillRect(option.rect, QColor("#2a2d2e"))
        else:
            painter.fillRect(option.rect, QColor("#1e2428"))

        # Draw completion text
        painter.setPen(QColor("#cccccc"))
        font = painter.font()
        font.setFamily("Roboto Mono")
        painter.setFont(font)

        text_rect = option.rect.adjusted(8, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, completion)

        # Draw snippet preview
        if completion in self.snippets:
            snippet = self.snippets[completion].split("\n")[0].strip()
            if len(snippet) > 35:
                snippet = snippet[:32] + "..."

            painter.setPen(QColor("#888888"))
            font.setItalic(True)
            painter.setFont(font)

            preview_rect = option.rect.adjusted(180, 0, -8, 0)
            painter.drawText(
                preview_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                snippet,
            )

        painter.restore()

    def sizeHint(self, option, index):
        return option.rect.size().expandedTo(self.parent().minimumSize())


def _create_format(color: str, bold=False, italic=False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


def _get_format_for_token(token_type: Token) -> QTextCharFormat:
    if token_type in TOKEN_COLORS:
        return _create_format(*TOKEN_COLORS[token_type])

    parent = token_type.parent
    while parent is not None:
        if parent in TOKEN_COLORS:
            return _create_format(*TOKEN_COLORS[parent])
        parent = parent.parent
    return _create_format("#d4d4d4")


class UniversalHighlighter(QSyntaxHighlighter):
    def __init__(self, document, lexer):
        super().__init__(document)
        self.lexer = lexer
        self._format_cache = {}
        self._block_tokens = {}
        self._last_text_hash = None

    def get_format(self, token_type):
        if token_type not in self._format_cache:
            self._format_cache[token_type] = _get_format_for_token(token_type)
        return self._format_cache[token_type]

    def _tokenize_document(self):
        full_text = self.document().toPlainText()
        current_hash = hash(full_text)

        if current_hash == self._last_text_hash:
            return

        self._last_text_hash = current_hash
        self._block_tokens = {}

        current_line = 0
        current_col = 0

        try:
            for token_type, token_value in lex(full_text, self.lexer):
                lines = token_value.split("\n")
                for i, line_part in enumerate(lines):
                    if i > 0:
                        current_line += 1
                        current_col = 0

                    if line_part and token_type not in (Token.Text, Token.Whitespace):
                        self._block_tokens.setdefault(current_line, []).append(
                            (current_col, len(line_part), token_type)
                        )
                    current_col += len(line_part)
        except Exception:
            pass

    def highlightBlock(self, text):
        if not PYGMENTS_AVAILABLE:
            return

        self._tokenize_document()
        block_num = self.currentBlock().blockNumber()

        for col, length, token_type in self._block_tokens.get(block_num, []):
            self.setFormat(col, length, self.get_format(token_type))


LANGUAGE_NAMES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".md": "Markdown",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".java": "Java",
    ".rs": "Rust",
    ".go": "Go",
    ".ts": "TypeScript",
    ".qss": "QSS",
    ".sh": "Bash",
    ".yaml": "YAML",
}


def get_language_name(file_path: str) -> str:
    if not file_path:
        return "Plain Text"
    path = Path(file_path)
    return LANGUAGE_NAMES.get(path.suffix.lower(), "Plain Text")


def get_all_languages():
    if not PYGMENTS_AVAILABLE:
        return sorted(list(set(LANGUAGE_NAMES.values())))

    from pygments.lexers import get_all_lexers

    languages = set()
    for name, aliases, patterns, mimetypes in get_all_lexers():
        languages.add(name)
    return sorted(languages)


def create_completer(language_name):
    completions_data = LANGUAGE_COMPLETIONS.get(
        language_name, {"keywords": [], "snippets": {}}
    )
    keywords = completions_data["keywords"]
    snippets = completions_data["snippets"]

    all_items = list(set(keywords + list(snippets.keys())))
    all_items.sort()

    completer = QCompleter(all_items)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

    # Configure popup
    popup = completer.popup()
    popup.setObjectName("completionPopup")
    popup.setMinimumSize(350, 150)
    popup.setMaximumHeight(300)

    # Set custom delegate
    delegate = CompletionDelegate(snippets, popup)
    popup.setItemDelegate(delegate)

    # Store snippets
    completer.snippets = snippets

    return completer


def create_highlighter(document, file_path):
    if not PYGMENTS_AVAILABLE or not file_path:
        return None, "Plain Text"

    lang_name = get_language_name(file_path)
    ext = Path(file_path).suffix.lower()

    try:
        if ext == ".qss":
            lexer = get_lexer_by_name("css", stripnl=False)
        else:
            lexer = get_lexer_for_filename(file_path, stripnl=False)

        return UniversalHighlighter(document, lexer), lang_name
    except ClassNotFound:
        return None, "Plain Text"


def create_highlighter_by_name(document, language_name):
    if not PYGMENTS_AVAILABLE or language_name == "Plain Text":
        return None, "Plain Text"

    try:
        alias = DISPLAY_NAME_TO_ALIAS.get(language_name, language_name).lower()
        lexer = get_lexer_by_name(alias, stripnl=False)
        return UniversalHighlighter(document, lexer), language_name
    except ClassNotFound:
        return None, "Plain Text"
