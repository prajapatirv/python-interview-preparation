"""Shared fixtures. Most tests run against a tiny throw-away repo so they don't depend on
(or modify) the real python-interview-prep folder; test_real_repo.py covers the real one."""
import json
import textwrap

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app


def events(resp):
    """Parse an SSE response body into a list of dicts."""
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    write(tmp_path / "01_demo" / "01_alpha.py", '''
        """
        Alpha demo: prints two lines.
        """
        # ------ part one
        print("hello")
        # EXPERIMENT: change the greeting
        # ------ part two
        print("world")
        ''')
    write(tmp_path / "01_demo" / "02_beta.py", '''
        def section(title):
            print(title)

        section("first")
        section("second")
        ''')
    write(tmp_path / "01_demo" / "03_fails.py", "import sys\nprint('boom', file=sys.stderr)\nsys.exit(3)\n")
    write(tmp_path / "01_demo" / "_live_leftover.py", "print('temp file must be ignored')\n")
    write(tmp_path / "02_checks" / "tests" / "test_math.py", "def test_add():\n    assert 1 + 1 == 2\n")
    write(tmp_path / "02_checks" / "01_helper.py", "print('helper')\n")
    write(tmp_path / "deep_dive" / "README.md", '''
        | # | Topic | Runnable companion |
        |---|---|---|
        | [01](01_demo_doc.md) | **Demo topic** | [`01_alpha.py`](../01_demo/01_alpha.py) |
        | [02](02_checks_doc.md) | **Checks topic** | [`02_checks/`](../02_checks/) |
        ''')
    write(tmp_path / "deep_dive" / "01_demo_doc.md", "# Demo doc\n\nSome **bold** text.\n")
    monkeypatch.setattr(config, "PREP_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def client(fake_repo):
    return TestClient(create_app())


@pytest.fixture
def allow_edit(monkeypatch):
    monkeypatch.setattr(config, "ALLOW_EDIT", True)
