"""Reads ``shared/cross-stack-pairs.md``: which Java and Python programs teach the same topic.

Each table row is ``| topic | Java links | Python links |``. Links are relative to the ``shared/``
folder. Ids follow each runner's catalog:

- Java: the path under ``java/java-interview-prep/examples/`` (``12_kafka/01_x.java``);
- Python: the path under ``python/python-interview-prep/`` (``06_kafka/03_x.py``), or
  ``<folder>/::pytest`` for a link to a whole folder (its test suite).
"""
import re
from pathlib import Path

JAVA_PREFIX = "../java/java-interview-prep/examples/"
PYTHON_PREFIX = "../python/python-interview-prep/"
ROW_RE = re.compile(r"^\|(?P<topic>[^|]+)\|(?P<java>[^|]*)\|(?P<python>[^|]*)\|\s*$")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def _ids(cell: str, prefix: str, folder_suffix: str = "") -> list[str]:
    out = []
    for target in LINK_RE.findall(cell):
        if target.startswith(prefix):
            rel = target[len(prefix):]
            out.append(rel.rstrip("/") + "/" + folder_suffix if rel.endswith("/") and folder_suffix else rel)
    return out


def parse(text: str) -> list[dict]:
    """``[{topic, java: [ids], python: [ids], targets: [raw links]}]`` for every data row."""
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line.strip())
        if not m or not LINK_RE.search(line):
            continue                                          # header, separator, prose
        rows.append({"topic": m["topic"].strip(),
                     "java": _ids(m["java"], JAVA_PREFIX),
                     "python": _ids(m["python"], PYTHON_PREFIX, "::pytest"),
                     "targets": LINK_RE.findall(m["java"]) + LINK_RE.findall(m["python"])})
    return rows


def load(path: Path) -> list[dict]:
    return parse(path.read_text(encoding="utf-8")) if path.is_file() else []


def twins_of(rows: list[dict], stack: str, example_id: str) -> list[dict]:
    """The other stack's programs for one example: ``[{topic, id}]`` (deduplicated, table order)."""
    other = "java" if stack == "python" else "python"
    out, seen = [], set()
    for r in rows:
        if example_id in r[stack]:
            for i in r[other]:
                if i not in seen:
                    seen.add(i)
                    out.append({"topic": r["topic"], "id": i})
    return out
