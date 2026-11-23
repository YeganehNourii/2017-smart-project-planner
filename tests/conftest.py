from datetime import date
from pathlib import Path

import pytest

from planner import Project, Task

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "samples" / "campus-app.json"


def T(id, duration=1, deps=(), **kw):
    """Short helper: T("b", 2, ["a"])."""
    return Task(id=id, name=kw.pop("name", id.upper()), duration=duration, depends_on=tuple(deps), **kw)


def make_project(*tasks, start=date(2026, 3, 2)):
    return Project.from_tasks("Test", start, tasks)


@pytest.fixture
def textbook():
    """A(3) → B(2), C(4) → D(2). Critical: A, C, D; B has 2 days slack."""
    return make_project(T("A", 3), T("B", 2, ["A"]), T("C", 4, ["A"]), T("D", 2, ["B", "C"]))


@pytest.fixture
def sample_project():
    from planner.serialization import load_json

    return load_json(str(SAMPLE))
