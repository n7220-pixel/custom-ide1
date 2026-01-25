# Copyright (c) 2026 n7220-pixel
# SPDX-License-Identifier: MIT
# See LICENSE.txt for more information.

# Syntax highlighting using Pygments.
# Supports 500+ languages.

from pathlib import Path
from re import PatternError

from pygments.token import Punctuation
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

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
    Token.Number: ("#b5cea8", False, False),
    Token.Comment: ("#6a9955", False, True),
    Token.Operator: ("#d4d4d4", False, False),
    Token.Punctuation: ("#d4d4d4", False, False),
    Token.Text: ("#d4d4d4", False, False),
    Token.Error: ("#f44747", False, False),
}


def _create_format(color: str, bold=False, italic=False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


def _get_format_for_token(token_type: Token) -> QTextCharFormat:
    # Exact match
    if token_type in TOKEN_COLORS:
        color, bold, italic = TOKEN_COLORS[token_type]
        return _create_format(color, bold, italic)

    # Walk up parent tokens
    parent = token_type.parent
    while parent is not None:
        if parent in TOKEN_COLORS:
            color, bold, italic = TOKEN_COLORS[parent]
            return _create_format(color, bold, italic)
        parent = parent.parent

    # Default
    return _create_format("#d4d4d4")


class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, document, lexer):
        super().__init__(document)
        self.lexer = lexer
        self._format_cache = {}

    def get_format(self, token_type):
        if token_type not in self._format_cache:
            self._format_cache[token_type] = _get_format_for_token(token_type)
        return self._format_cache[token_type]

    def highlightBlock(self, text):
        if not text or not PYGMENTS_AVAILABLE:
            return

        index = 0
        try:
            for token_type, token_value in lex(text, self.lexer):
                length = len(token_value)
                if token_type not in (Token.Text, Token.Whitespace):
                    fmt = self.get_format(token_type)
                    self.setFormat(index, length, fmt)
                index += length
        except Exception:
            pass  # Fail gracefully if lexer errors


class FullDocumentHighlighter(QSyntaxHighlighter):
    def __init__(self, document, lexer):
        super().__init__(document)
        self.lexer = lexer
        self._format_cache = {}
        self._block_tokens = {}
        self._document_hash = None

    def get_format(self, token_type):
        if token_type not in self._format_cache:
            self._format_cache[token_type] = _get_format_for_token(token_type)
        return self._format_cache[token_type]

    def _tokenize_document(self):
        doc = self.document()
        full_text = doc.toPlainText()
        new_hash = hash(full_text)
        if new_hash == self._document_hash:
            return
        self._document_hash = new_hash
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
        if not text or not PYGMENTS_AVAILABLE:
            return
        # NOTE: This is computationally expensive for large files
        self._tokenize_document()
        block_num = self.currentBlock().blockNumber()
        for col, length, token_type in self._block_tokens.get(block_num, []):
            fmt = self.get_format(token_type)
            self.setFormat(col, length, fmt)


# Full list of languages/extensions
LANGUAGE_NAMES = {
    ".py": "Python",
    ".pyw": "Python",
    ".pyx": "Cython",
    ".pxd": "Cython",
    ".js": "JavaScript",
    ".jsx": "JavaScript (JSX)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (TSX)",
    ".html": "HTML",
    ".htm": "HTML",
    ".xhtml": "XHTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".json5": "JSON5",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".svg": "SVG",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Plain Text",
    ".c": "C",
    ".h": "C Header",
    ".cpp": "C++",
    ".cxx": "C++",
    ".cc": "C++",
    ".hpp": "C++ Header",
    ".hxx": "C++ Header",
    ".cs": "C#",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin Script",
    ".scala": "Scala",
    ".go": "Go",
    ".rs": "Rust",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".rb": "Ruby",
    ".php": "PHP",
    ".pl": "Perl",
    ".pm": "Perl Module",
    ".lua": "Lua",
    ".r": "R",
    ".jl": "Julia",
    ".hs": "Haskell",
    ".lhs": "Literate Haskell",
    ".ml": "OCaml",
    ".mli": "OCaml Interface",
    ".fs": "F#",
    ".fsx": "F# Script",
    ".ex": "Elixir",
    ".exs": "Elixir Script",
    ".erl": "Erlang",
    ".hrl": "Erlang Header",
    ".clj": "Clojure",
    ".cljs": "ClojureScript",
    ".lisp": "Common Lisp",
    ".cl": "Common Lisp",
    ".el": "Emacs Lisp",
    ".scm": "Scheme",
    ".rkt": "Racket",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".fish": "Fish",
    ".ps1": "PowerShell",
    ".psm1": "PowerShell Module",
    ".bat": "Batch",
    ".cmd": "Batch",
    ".asm": "Assembly",
    ".s": "Assembly",
    ".S": "Assembly",
    ".v": "Verilog",
    ".sv": "SystemVerilog",
    ".vhd": "VHDL",
    ".vhdl": "VHDL",
    ".tex": "LaTeX",
    ".latex": "LaTeX",
    ".bib": "BibTeX",
    ".makefile": "Makefile",
    ".mk": "Makefile",
    ".cmake": "CMake",
    ".gradle": "Gradle",
    ".groovy": "Groovy",
    ".dockerfile": "Dockerfile",
    ".docker": "Dockerfile",
    ".nginx": "Nginx",
    ".conf": "Config",
    ".ini": "INI",
    ".cfg": "Config",
    ".properties": "Properties",
    ".env": "Environment",
    ".gitignore": "Git Ignore",
    ".gitattributes": "Git Attributes",
    ".editorconfig": "EditorConfig",
    ".qss": "QSS",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".astro": "Astro",
    ".zig": "Zig",
    ".nim": "Nim",
    ".d": "D",
    ".pas": "Pascal",
    ".pp": "Pascal",
    ".f90": "Fortran",
    ".f95": "Fortran",
    ".f03": "Fortran",
    ".f": "Fortran",
    ".cob": "COBOL",
    ".cbl": "COBOL",
    ".ada": "Ada",
    ".adb": "Ada",
    ".ads": "Ada",
    ".pro": "Prolog",
    ".tcl": "Tcl",
    ".awk": "AWK",
    ".sed": "sed",
    ".vim": "Vim Script",
    ".applescript": "AppleScript",
}

FULL_DOCUMENT_LANGUAGES = {
    ".html",
    ".htm",
    ".xhtml",
    ".vue",
    ".svelte",
    ".astro",
    ".php",
    ".erb",
    ".ejs",
    ".jinja",
    ".jinja2",
    ".twig",
}


def get_language_name(file_path: str) -> str:
    if not file_path:
        return "Plain Text"
    path = Path(file_path)
    ext = path.suffix.lower()
    special_names = {
        "makefile": "Makefile",
        "gnumakefile": "Makefile",
        "dockerfile": "Dockerfile",
        "cmakelists.txt": "CMake",
        "rakefile": "Ruby",
        "gemfile": "Ruby",
        ".bashrc": "Bash",
        ".bash_profile": "Bash",
        ".zshrc": "Zsh",
        ".profile": "Shell",
        ".gitignore": "Git Ignore",
        ".gitattributes": "Git Attributes",
        ".editorconfig": "EditorConfig",
    }
    if path.name.lower() in special_names:
        return special_names[path.name.lower()]
    return LANGUAGE_NAMES.get(ext, "Plain Text")


def get_all_languages():
    """Returns a sorted list of all unique supported language names."""
    return sorted(list(set(LANGUAGE_NAMES.values())))


def create_highlighter(document, file_path):
    """Creates a highlighter based on the filename/extension."""
    if not PYGMENTS_AVAILABLE or not file_path:
        return None, "Plain Text"

    language_name = get_language_name(file_path)
    ext = Path(file_path).suffix.lower()

    try:
        lexer = get_lexer_for_filename(file_path, stripnl=False, stripall=False)
        if ext in FULL_DOCUMENT_LANGUAGES:
            return FullDocumentHighlighter(document, lexer), language_name
        return PygmentsHighlighter(document, lexer), language_name
    except ClassNotFound:
        return None, "Plain Text"


def create_highlighter_by_name(document, language_name):
    """Creates a highlighter based on the language name (e.g. 'Python')."""
    if not PYGMENTS_AVAILABLE or not language_name or language_name == "Plain Text":
        return None, "Plain Text"

    try:
        # Map common display names to pygments aliases if necessary
        lexer = get_lexer_by_name(language_name, stripnl=False, stripall=False)

        # Check if this language requires full document parsing
        is_full_doc = False
        # Reverse check extension for full doc languages
        # This is an estimation, as we only have the name here
        for ext, name in LANGUAGE_NAMES.items():
            if name == language_name and ext in FULL_DOCUMENT_LANGUAGES:
                is_full_doc = True
                break

        if is_full_doc:
            return FullDocumentHighlighter(document, lexer), language_name
        return PygmentsHighlighter(document, lexer), language_name
    except ClassNotFound:
        return None, "Plain Text"
