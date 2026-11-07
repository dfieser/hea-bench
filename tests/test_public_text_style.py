"""Public text carries no em dash and no semicolon (owner rule, 2026-11-07).

The owner's standing rule: every piece of public-facing text, in the
repository and in the program, reads as written by a person, so prose
never uses an em dash or a semicolon. Version logs in particular never
carry either mark. This test makes the rule mechanical. It reads:

- the Markdown and text documents, with code blocks, inline code, URLs and
  HTML entities skipped, since they are not prose.
- the prose fields of the publishing metadata (PyPI, the MCP registry,
  Zenodo, Glama).
- web/index.html: page text, user-facing attributes and the What's-new
  history, with LaTeX math skipped, since LaTeX spacing uses the mark.
- every string literal in src/hea_bench, docstrings included, and in the
  web app's scripts.

JavaScript and Python statements use semicolons as code, so only string
literals count there. A lone em dash used as an empty-value placeholder is
a symbol, not punctuation, and stays. Text quoted verbatim from someone
else, such as a published paper's title or an upstream dataset label, is
listed in ``VERBATIM`` with the reason.

A failure names each place. Fix it by rewriting the sentence with a
period or a comma (run the ai-writing-cleanup skill on new public text),
never by adding it to ``VERBATIM`` unless it is a quotation.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: A semicolon, an em dash, or a spaced en dash or double hyphen used as one.
MARKS = re.compile(r";|—| -- | – ")

#: An em dash alone (after trimming spaces and tags) is the app's
#: empty-value placeholder.
PLACEHOLDER = re.compile(r"^\s*(<[^>]*>)*\s*—\s*(<[^>]*>)*\s*$")

#: Documents that are not ours to edit: verbatim upstream or standard texts.
NOT_OURS = {
    "CODE_OF_CONDUCT.md",  # the Contributor Covenant, adopted verbatim
    "data/raw/chizhevskiy2026/UPSTREAM_README.md",  # the upstream author's README
}

#: Exact substrings that quote someone else verbatim, per file ("*" for any
#: file), with the reason.
VERBATIM: dict[str, list[str]] = {
    # The published paper's author list, in the journal's own citation format
    # (Materials 2026, 19, 3075).
    "*": ["Fieser, D.; Dewanjee, U.; Hu, A."],
    # Published paper titles, quoted exactly in the References view.
    "web/index.html": [
        "Cohesion in alloys—Fundamentals of a semi-empirical model",
        "Oxide pyrochlores — A review",
    ],
}

#: "(—)" is the unit label of a dimensionless quantity, a symbol like the
#: empty-value placeholder. The saved-results CSV uses it in column names.
UNITLESS = "(—)"

#: Generated copies of the fingerprinted data modules (see FINGERPRINTED),
#: skipped for the same reason as their sources.
GENERATED_FROM_FINGERPRINTED = re.compile(
    r"// BEGIN GENERATED: PROVENANCE_TABLES.*?// END GENERATED: PROVENANCE_TABLES", re.S
)

#: The two data modules whose bytes are SHA-256 fingerprinted and published
#: (hea_bench.descriptors.elements._DATA_FILES). They hold reference data,
#: not prose.
FINGERPRINTED = {
    "src/hea_bench/descriptors/data/elemental.py",
    "src/hea_bench/descriptors/data/provenance.py",
}


def _tracked() -> list[str]:
    try:
        listed = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("needs a git checkout to know which files are tracked")
    return listed.stdout.split()


def _allowed(path: str, text: str) -> str:
    for quote in (*VERBATIM.get(path, ()), *VERBATIM["*"]):
        text = text.replace(quote, "")
    return text


def _hits(path: str, line: int, text: str) -> list[str]:
    text = _ENTITY.sub("", _allowed(path, text)).replace(UNITLESS, "")
    if PLACEHOLDER.match(text) or not MARKS.search(text):
        return []
    return [f"{path}:{line}: {text.strip()[:120]!r}"]


# -- documents -----------------------------------------------------------------

_INLINE_CODE = re.compile(r"(`+).+?\1")
_URL = re.compile(r"https?://\S+|\]\([^)]*\)")
_ENTITY = re.compile(r"&#?\w+;")


def _document_hits(path: str) -> list[str]:
    hits, fenced = [], False
    for number, line in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        prose = _ENTITY.sub("", _URL.sub("", _INLINE_CODE.sub("", line)))
        hits += _hits(path, number, prose)
    return hits


def _documents(tracked: list[str]) -> list[str]:
    return [
        path
        for path in tracked
        if path.endswith((".md", ".txt", ".cff"))
        and path not in NOT_OURS
        and not path.startswith(("tests/", "web/mathjax/"))
        and "LICENSE" not in path
    ]


def test_documents_have_no_em_dash_or_semicolon() -> None:
    hits = [hit for path in _documents(_tracked()) for hit in _document_hits(path)]
    assert not hits, _report(hits)


def test_publishing_metadata_has_no_em_dash_or_semicolon() -> None:
    hits = []
    for path in ("server.json", ".zenodo.json", "glama.json"):
        file = ROOT / path
        if file.exists():
            for text in _json_strings(json.loads(file.read_text(encoding="utf-8"))):
                hits += _hits(path, 0, text)
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    description = re.search(r'^description = "(.*)"$', pyproject, re.M)
    hits += _hits("pyproject.toml", 0, description.group(1) if description else "")
    assert not hits, _report(hits)


def _json_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _json_strings(item)


# -- the web app -----------------------------------------------------------------

_MATH = re.compile(r"\\\(.*?\\\)|\\\[.*?\\\]|\$\$.*?\$\$", re.S)
_VISIBLE_ATTRIBUTES = {"title", "alt", "aria-label", "placeholder", "content"}


class _PageText(HTMLParser):
    """Page text and user-facing attributes, outside <script> and <style>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[tuple[int, str]] = []
        self.scripts: list[tuple[int, str]] = []
        self._skip: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = tag
        named = dict(attrs)
        for name, value in attrs:
            if not value or name not in _VISIBLE_ATTRIBUTES:
                continue
            if name == "content" and not ({"name", "property"} & set(named)):
                continue  # http-equiv headers such as "text/html; charset=UTF-8"
            self.parts.append((self.getpos()[0], value))

    def handle_endtag(self, tag):
        if tag == self._skip:
            self._skip = None

    def handle_data(self, data):
        if self._skip == "script":
            self.scripts.append((self.getpos()[0], data))
        elif self._skip is None and data.strip():
            self.parts.append((self.getpos()[0], data))


def test_web_page_text_has_no_em_dash_or_semicolon() -> None:
    page = _PageText()
    page.feed((ROOT / "web" / "index.html").read_text(encoding="utf-8"))
    # A displayed equation can span several text chunks, so strip math from
    # the joined text and keep each chunk boundary.
    joined = "\x00".join(text for _, text in page.parts)
    joined = _MATH.sub(lambda m: "\x00" * m.group(0).count("\x00"), joined)
    hits = []
    for (line, _), text in zip(page.parts, joined.split("\x00")):
        hits += _hits("web/index.html", line, text)
    assert not hits, _report(hits)


#: A keyword after which a slash opens a regular expression, not a division.
_KEYWORD_BEFORE = re.compile(
    r"(?<![\w$])(?:return|typeof|case|do|else|in|of|new|delete|void|throw|instanceof|yield|await)"
    r"\s*\Z"
)


def _js_strings(code: str):
    """(offset, text) for every string and template literal in ``code``.

    A small tokenizer: it skips comments and regular-expression literals so
    that a quote inside either never opens a string, and it drops the
    ``${...}`` expressions of template literals.
    """
    i, n, previous = 0, len(code), ""
    while i < n:
        char = code[i]
        if code.startswith("//", i):
            end = code.find("\n", i)
            i = n if end < 0 else end
            continue
        if code.startswith("/*", i):
            end = code.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if char in "'\"`":
            start, j, text = i, i + 1, []
            while j < n and code[j] != char:
                if code[j] == "\\":
                    j += 2
                    continue
                if char != "`" and code[j] == "\n":
                    break
                if char == "`" and code.startswith("${", j):
                    depth, j = 1, j + 2
                    while j < n and depth:
                        depth += {"{": 1, "}": -1}.get(code[j], 0)
                        j += 1
                    text.append("x")  # a value, so "${a}–${b}" reads as a range
                    continue
                text.append(code[j])
                j += 1
            yield start, "".join(text)
            i, previous = j + 1, char
            continue
        if char == "/" and (
            previous == "" or previous in "(,=:[!&|?{};+-*%<>~^" or _KEYWORD_BEFORE.search(code, 0, i)
        ):
            j, in_class = i + 1, False
            while j < n and code[j] != "\n":
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == "[":
                    in_class = True
                elif code[j] == "]":
                    in_class = False
                elif code[j] == "/" and not in_class:
                    break
                j += 1
            i, previous = j + 1, "/"
            continue
        if not char.isspace():
            previous = char
        i += 1


_STYLE_ATTRIBUTE = re.compile(r"""\bstyle\s*=\s*("[^"]*"|'[^']*')""")
_PROSE_ATTRIBUTE = re.compile(r"""\b(?:title|alt|aria-label|placeholder)\s*=\s*("[^"]*"|'[^']*')""")
_MIME = re.compile(r"^[\w.+-]+/[\w.+-]+;\s*charset=[\w-]+$")


def _string_prose(text: str) -> str:
    """What a reader sees of a script string: markup text and prose attributes.

    Inline CSS and tag syntax are code. A bare ";" (a CSV field separator)
    and a MIME type are data.
    """
    if text.strip() == ";" or _MIME.match(text.strip()):
        return ""
    text = _STYLE_ATTRIBUTE.sub("", text)
    attributes = " ".join(m.group(1)[1:-1] for m in _PROSE_ATTRIBUTE.finditer(text))
    return re.sub(r"<[^>]*>", " ", text) + " " + attributes


def _script_hits(path: str, code: str, first_line: int = 1) -> list[str]:
    code = GENERATED_FROM_FINGERPRINTED.sub(lambda m: "\n" * m.group(0).count("\n"), code)
    hits = []
    for offset, text in _js_strings(code):
        line = first_line + code.count("\n", 0, offset)
        # Math in a script string is escaped ("\\[ ... \\]") before it reaches the page.
        hits += _hits(path, line, _string_prose(_MATH.sub("", text.replace("\\\\", "\\"))))
    return hits


def test_web_scripts_have_no_em_dash_or_semicolon_in_strings() -> None:
    hits = []
    for name in ("hea-features.js", "hea-calculator-core.js", "hea-engine.js", "hea-engine-worker.js"):
        hits += _script_hits(f"web/{name}", (ROOT / "web" / name).read_text(encoding="utf-8"))
    page = _PageText()
    page.feed((ROOT / "web" / "index.html").read_text(encoding="utf-8"))
    for line, code in page.scripts:
        if code.lstrip().startswith("{"):  # JSON-LD: a structured-data object, see metadata
            continue
        hits += _script_hits("web/index.html", code, line)
    assert not hits, _report(hits)


# -- the Python package ------------------------------------------------------------


def test_package_strings_have_no_em_dash_or_semicolon() -> None:
    hits = []
    for file in sorted((ROOT / "src" / "hea_bench").rglob("*.py")):
        path = file.relative_to(ROOT).as_posix()
        if path in FINGERPRINTED:
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.strip() == ";":  # a CSV delimiter, not prose
                    continue
                hits += _hits(path, node.lineno, node.value)
    assert not hits, _report(hits)


def _report(hits: list[str]) -> str:
    shown = "\n  ".join(hits[:60])
    more = f"\n  ... and {len(hits) - 60} more" if len(hits) > 60 else ""
    return (
        f"{len(hits)} place(s) use an em dash or a semicolon in public text (owner rule, "
        f"2026-11-07):\n  {shown}{more}\nRewrite each with a period or a comma. Run the "
        "ai-writing-cleanup skill on new public text."
    )
