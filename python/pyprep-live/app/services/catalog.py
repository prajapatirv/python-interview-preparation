"""Discovers topics/examples from the repo on disk - no hand-maintained manifest.

Everything the UI shows (title, description, sections, experiments, dependencies) is derived
from the files themselves, so adding NN_new_example.py to the repo makes it appear in the app.
"""
import ast
import re
import threading
from dataclasses import asdict, dataclass, field

from .. import config
from . import docs

TOPIC_RE = re.compile(r"^\d{2}_")
SECTION_RE = re.compile(r"^#\s*-{5,}\s*(.+?)\s*$")                 # '# ------ section title'
CALL_SECTION_RE = re.compile(r"""^\s*(?:section|banner|header)\(\s*["'](.+?)["']""")   # section("title")
EXPERIMENT_RE = re.compile(r"^\s*#\s*EXPERIMENT:\s*(.+?)\s*$")
TEST_FUNC_RE = re.compile(r"^(?:async\s+)?def test_", re.M)
SKIP_FILES = {"conftest.py", "__init__.py"}
TEMP_PREFIX = "_live_"                                              # runner's edited-code temp files

# import name -> pip package, for the "needs" badge
THIRD_PARTY = {
    "pandas": "pandas", "numpy": "numpy", "fastapi": "fastapi", "uvicorn": "uvicorn",
    "pydantic": "pydantic", "httpx": "httpx", "pytest": "pytest", "redis": "redis",
    "confluent_kafka": "confluent-kafka", "boto3": "boto3", "flask": "flask",
}
# examples that only fully execute against external infrastructure; here they are explain-only (no broker is provided)
NEEDS_INFRA = {"confluent_kafka": "a live Kafka broker"}


@dataclass
class Example:
    id: str                       # '01_python_core/03_decorators.py'
    topic: str
    file: str
    title: str
    description: str
    sections: list = field(default_factory=list)      # [{line, title}]
    experiments: list = field(default_factory=list)   # [{line, text}]
    docs: list = field(default_factory=list)          # [{id, title}] deep-dive documents
    needs: list = field(default_factory=list)
    infra: str = ""
    kind: str = "script"          # script | suite
    lines: int = 0

    @property
    def is_suite(self) -> bool:
        return self.kind == "suite"


def _title(stem: str) -> str:
    stem = re.sub(r"^\d+_", "", stem)
    return stem.replace("_", " ").strip().title()


def _first_doc_line(doc: str) -> str:
    # docstrings often start with a blank line - keep the first real line
    return next((ln.strip() for ln in doc.splitlines() if ln.strip()), "")


def analyse_source(src: str) -> dict:
    try:
        tree = ast.parse(src)
        doc = ast.get_docstring(tree) or ""
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                mods.add(n.module.split(".")[0])
    except SyntaxError:
        doc, mods = "", set()
    banners, calls, experiments = [], [], []
    lines = src.splitlines()
    for i, line in enumerate(lines, 1):
        if m := SECTION_RE.match(line):
            banners.append({"line": i, "title": m.group(1)})
        elif m := CALL_SECTION_RE.match(line):
            calls.append({"line": i, "title": m.group(1)})
        if m := EXPERIMENT_RE.match(line):
            experiments.append({"line": i, "text": m.group(1)})
    return {
        "doc": doc,
        # '# ------' banners win; files that call a section("...") helper are the fallback
        "sections": banners or calls,
        "experiments": experiments,
        "needs": sorted({THIRD_PARTY[m] for m in mods if m in THIRD_PARTY}),
        "infra": next((NEEDS_INFRA[m] for m in mods if m in NEEDS_INFRA), ""),
        "lines": len(lines),
        "has_tests": bool(TEST_FUNC_RE.search(src)),
    }


class Catalog:
    """Snapshot of what is on disk; `reload()` swaps in a fresh one."""

    def __init__(self):
        self._lock = threading.Lock()
        self.topics: list = []
        self.index: dict[str, Example] = {}
        self.error: str | None = None
        self.reload()

    def reload(self) -> int:
        topics, index, error = self._scan()
        with self._lock:                       # swap all three together
            self.topics, self.index, self.error = topics, index, error
        return len(index)

    def get(self, example_id: str) -> Example | None:
        return self.index.get(example_id)

    @staticmethod
    def _scan():
        root = config.PREP_ROOT
        if not root.exists():
            return [], {}, f"PREP_ROOT not found: {root}"
        deep = docs.build_map(root)
        topics, index = [], {}
        for folder in sorted(p for p in root.iterdir() if p.is_dir() and TOPIC_RE.match(p.name)):
            items, any_tests = [], (folder / "tests").is_dir()
            for py in sorted(folder.glob("*.py")):
                if py.name in SKIP_FILES or py.name.startswith(TEMP_PREFIX):
                    continue
                a = analyse_source(py.read_text(encoding="utf-8", errors="ignore"))
                any_tests = any_tests or a["has_tests"]
                items.append(Example(
                    id=f"{folder.name}/{py.name}", topic=folder.name, file=py.name,
                    title=_title(py.stem), description=_first_doc_line(a["doc"]),
                    sections=a["sections"], experiments=a["experiments"],
                    docs=docs.docs_for(deep, folder.name, py.name), needs=a["needs"],
                    infra=a["infra"], lines=a["lines"]))
            if any_tests:      # tests/ dir, or embedded test_* functions (topic 11)
                items.append(Example(
                    id=f"{folder.name}/::pytest", topic=folder.name, file="pytest",
                    title="Run the test suite (pytest -v)",
                    description=f"Runs every test under {folder.name}", needs=["pytest"],
                    docs=docs.docs_for(deep, folder.name, ""), kind="suite"))
            for e in items:
                index[e.id] = e
            readme = folder / "README.md"
            topics.append({"id": folder.name, "title": _title(folder.name),
                           "readme": readme.read_text(encoding="utf-8", errors="ignore") if readme.exists() else "",
                           "examples": [asdict(e) for e in items]})
        return topics, index, None


def read_source(example: Example) -> str:
    if example.is_suite:
        return ""
    return (config.PREP_ROOT / example.topic / example.file).read_text(encoding="utf-8", errors="ignore")
