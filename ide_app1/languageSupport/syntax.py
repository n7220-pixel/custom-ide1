from PyQt6.QtGui import (
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QFont
)
from PyQt6.QtCore import QRegularExpression
from pathlib import Path

HTML_STATE = 0
SCRIPT_STATE = 1
STYLE_STATE = 2

class BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, document, rules):
        super().__init__(document)
        self.rules = rules

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt
                )

class HtmlHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.html_rules = html_rules()
        self.js_rules = javascript_rules()
        self.css_rules = css_rules()

        self.script_start = QRegularExpression(r"<script\b[^>]*>")
        self.script_end = QRegularExpression(r"</script>")
        self.style_start = QRegularExpression(r"<style\b[^>]*>")
        self.style_end = QRegularExpression(r"</style>")

    def highlightBlock(self, text):
        state = self.previousBlockState()
        if state == -1:
            state = HTML_STATE

        # HTML
        if state == HTML_STATE:
            for pattern, fmt in self.html_rules:
                it = pattern.globalMatch(text)
                while it.hasNext():
                    m = it.next()
                    self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

            if self.script_start.match(text).hasMatch():
                self.setCurrentBlockState(SCRIPT_STATE)
                return

            if self.style_start.match(text).hasMatch():
                self.setCurrentBlockState(STYLE_STATE)
                return

            self.setCurrentBlockState(HTML_STATE)
            return

        # SCRIPT
        if state == SCRIPT_STATE:
            for pattern, fmt in self.js_rules:
                it = pattern.globalMatch(text)
                while it.hasNext():
                    m = it.next()
                    self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

            if self.script_end.match(text).hasMatch():
                self.setCurrentBlockState(HTML_STATE)
            else:
                self.setCurrentBlockState(SCRIPT_STATE)
            return

        # STYLE
        if state == STYLE_STATE:
            for pattern, fmt in self.css_rules:
                it = pattern.globalMatch(text)
                while it.hasNext():
                    m = it.next()
                    self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

            if self.style_end.match(text).hasMatch():
                self.setCurrentBlockState(HTML_STATE)
            else:
                self.setCurrentBlockState(STYLE_STATE)
            return

def _fmt(color, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


def python_rules():
    keyword = _fmt("#569cd6", True)
    builtin = _fmt("#4ec9b0")
    function = _fmt("#dcdcaa")
    string = _fmt("#ce9178")
    comment = _fmt("#6a9955", italic=True)
    number = _fmt("#b5cea8")
    decorator = _fmt("#4ec9b0")
    
    keywords = [
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else",
        "except", "finally", "for", "from", "global", "if", "import",
        "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise",
        "return", "try", "while", "with", "yield"
    ]
    
    builtins = [
        "abs", "all", "any", "ascii", "bin", "bool", "bytes", "chr",
        "dict", "dir", "enumerate", "filter", "float", "format", "int",
        "len", "list", "map", "max", "min", "open", "print", "range",
        "repr", "set", "sorted", "str", "sum", "tuple", "type", "zip"
    ]

    return (
        [(QRegularExpression(fr"\b{k}\b"), keyword) for k in keywords] +
        [(QRegularExpression(fr"\b{b}\b"), builtin) for b in builtins] + [
            (QRegularExpression(r"@\w+"), decorator),
            (QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\()"), function),
            (QRegularExpression(r"\"\"\".*?\"\"\"|'''.*?'''"), string),
            (QRegularExpression(r"f?[\"'](?:\\.|[^\"'\\])*[\"']"), string),
            (QRegularExpression(r"\b\d+\.?\d*\b"), number),
            (QRegularExpression(r"#.*"), comment),
        ]
    )


def javascript_rules():
    keyword = _fmt("#569cd6", True)
    function = _fmt("#dcdcaa")
    string = _fmt("#ce9178")
    comment = _fmt("#6a9955", italic=True)
    number = _fmt("#b5cea8")
    
    keywords = [
        "async", "await", "break", "case", "catch", "class", "const",
        "continue", "debugger", "default", "delete", "do", "else",
        "export", "extends", "finally", "for", "function", "if",
        "import", "in", "instanceof", "let", "new", "return", "super",
        "switch", "this", "throw", "try", "typeof", "var", "void",
        "while", "with", "yield", "true", "false", "null", "undefined"
    ]
    
    return (
        [(QRegularExpression(fr"\b{k}\b"), keyword) for k in keywords] + [
            (QRegularExpression(r"\b[A-Za-z_$][A-Za-z0-9_$]*(?=\()"), function),
            (QRegularExpression(r"`(?:\\.|[^`\\])*`"), string),
            (QRegularExpression(r"[\"'](?:\\.|[^\"'\\])*[\"']"), string),
            (QRegularExpression(r"\b\d+\.?\d*\b"), number),
            (QRegularExpression(r"//.*"), comment),
            (QRegularExpression(r"/\*.*?\*/"), comment),
        ]
    )


def html_rules():
    tag = _fmt("#569cd6", True)
    attribute = _fmt("#9cdcfe")
    string = _fmt("#ce9178")
    comment = _fmt("#6a9955", italic=True)
    doctype = _fmt("#c586c0", True)
    
    return [
        (QRegularExpression(r"<!--[^-]*-(?:[^-][^-]*-)*->"), comment),
        (QRegularExpression(r"<!DOCTYPE[^>]*>"), doctype),
        (QRegularExpression(r"</?[a-zA-Z][a-zA-Z0-9]*[^>]*>"), tag),
        (QRegularExpression(r"\b[a-zA-Z-]+(?==)"), attribute),
        (QRegularExpression(r"\"[^\"]*\"|'[^']*'"), string),
    ]



def css_rules():
    selector = _fmt("#d7ba7d")
    property_name = _fmt("#9cdcfe")
    value = _fmt("#ce9178")
    comment = _fmt("#6a9955", italic=True)
    important = _fmt("#c586c0", True)
    number = _fmt("#b5cea8")
    
    return [
        (QRegularExpression(r"/\*.*?\*/"), comment),
        (QRegularExpression(r"[.#]?[a-zA-Z_][\w-]*(?=\s*\{)"), selector),
        (QRegularExpression(r"\b[a-zA-Z-]+(?=\s*:)"), property_name),
        (QRegularExpression(r"!important"), important),
        (QRegularExpression(r"#[0-9a-fA-F]{3,6}\b"), value),
        (QRegularExpression(r"\b\d+\.?\d*(px|em|rem|%|vh|vw|pt)?\b"), number),
        (QRegularExpression(r"\"[^\"]*\"|'[^']*'"), value),
    ]


def qss_rules():
    # QSS is similar to CSS
    return css_rules()


def json_rules():
    key = _fmt("#9cdcfe")
    string = _fmt("#ce9178")
    number = _fmt("#b5cea8")
    boolean = _fmt("#569cd6", True)
    null = _fmt("#569cd6", True)
    
    return [
        (QRegularExpression(r"\"[^\"]*\"(?=\s*:)"), key),
        (QRegularExpression(r":\s*\"[^\"]*\""), string),
        (QRegularExpression(r"\b(true|false)\b"), boolean),
        (QRegularExpression(r"\bnull\b"), null),
        (QRegularExpression(r"\b-?\d+\.?\d*([eE][+-]?\d+)?\b"), number),
    ]


def lua_rules():
    keyword = _fmt("#569cd6", True)
    function = _fmt("#dcdcaa")
    string = _fmt("#ce9178")
    comment = _fmt("#6a9955", italic=True)
    number = _fmt("#b5cea8")
    
    keywords = [
        "and", "break", "do", "else", "elseif", "end", "false", "for",
        "function", "if", "in", "local", "nil", "not", "or", "repeat",
        "return", "then", "true", "until", "while"
    ]
    
    return (
        [(QRegularExpression(fr"\b{k}\b"), keyword) for k in keywords] + [
            (QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\()"), function),
            (QRegularExpression(r"\[\[.*?\]\]"), string),
            (QRegularExpression(r"[\"'](?:\\.|[^\"'\\])*[\"']"), string),
            (QRegularExpression(r"\b\d+\.?\d*\b"), number),
            (QRegularExpression(r"--\[\[.*?\]\]"), comment),
            (QRegularExpression(r"--.*"), comment),
        ]
    )


LANGUAGES = {
    ".py": ("Python", python_rules),
    ".qss": ("QSS", qss_rules),
    ".css": ("CSS", css_rules),
    ".html": ("HTML", html_rules),
    ".htm": ("HTML", html_rules),
    ".js": ("JavaScript", javascript_rules),
    ".json": ("JSON", json_rules),
    ".lua": ("Lua", lua_rules),
}


def create_highlighter(document, file_path):
    ext = Path(file_path).suffix.lower()

    if ext in (".html", ".htm"):
        return HtmlHighlighter(document), "HTML"

    if ext in LANGUAGES:
        name, rule_fn = LANGUAGES[ext]
        return BaseHighlighter(document, rule_fn()), name
    return None, "Plain Text"