import sqlite3
from datetime import date

import pytest

from planner.graph import CycleError
from planner.models import Project, ValidationError
from planner.storage import NotFoundError, Repository
from tests.conftest import T


@pytest.fixture
def repo(tmp_path):
    with Repository(str(tmp_path / "test.db")) as r:
        yield r


def test_round_trip(repo, sample_project):
    repo.save_project(sample_project)
    loaded = repo.load_project(sample_project.name)
    assert loaded.start == sample_project.start
    assert list(loaded.tasks) == list(sample_project.tasks)  # order kept
    assert loaded.tasks == sample_project.tasks


def test_list_and_delete_projects(repo):
    repo.save_project(Project("b", date(2026, 1, 1)))
    repo.save_project(Project("a", date(2026, 1, 1)))
    assert repo.list_projects() == ["a", "b"]
    repo.delete_project("a")
    assert repo.list_projects() == ["b"]
    with pytest.raises(NotFoundError):
        repo.delete_project("a")
    with pytest.raises(NotFoundError):
        repo.load_project("a")


def test_save_replaces_existing(repo, sample_project):
    repo.save_project(sample_project)
    smaller = Project.from_tasks(sample_project.name, date(2026, 4, 1), [T("x", 2)])
    repo.save_project(smaller)
    loaded = repo.load_project(sample_project.name)
    assert list(loaded.tasks) == ["x"] and loaded.start == date(2026, 4, 1)
    count = repo.conn.execute("SELECT COUNT(*) FROM dependencies").fetchone()[0]
    assert count == 0  # old dependency rows were cascaded away


def test_task_operations(repo):
    repo.save_project(Project("p", date(2026, 1, 1)))
    repo.add_task("p", T("a", 2))
    repo.add_task("p", T("b", 1, ["a"], deadline=date(2026, 1, 9), owner="Sara", priority=1))
    repo.set_done("p", "a")
    p = repo.load_project("p")
    assert p.tasks["a"].done and p.tasks["b"].depends_on == ("a",)
    assert p.tasks["b"].deadline == date(2026, 1, 9) and p.tasks["b"].owner == "Sara"
    repo.set_done("p", "a", False)
    assert not repo.load_project("p").tasks["a"].done

    with pytest.raises(ValidationError, match="depend"):
        repo.delete_task("p", "a")
    repo.delete_task("p", "b")
    repo.delete_task("p", "a")
    assert repo.load_project("p").tasks == {}


def test_invalid_changes_are_not_saved(repo):
    repo.save_project(Project.from_tasks("p", date(2026, 1, 1), [T("a"), T("b", deps=["a"])]))
    with pytest.raises(CycleError):
        repo.add_task("p", T("c", deps=["c"]))
    with pytest.raises(ValidationError):
        repo.add_task("p", T("a"))
    with pytest.raises(NotFoundError):
        repo.add_task("missing", T("z"))
    assert list(repo.load_project("p").tasks) == ["a", "b"]


def test_database_constraints(repo):
    """The schema protects the data even when bypassing the Python layer."""
    repo.save_project(Project.from_tasks("p", date(2026, 1, 1), [T("a")]))
    pid = repo.conn.execute("SELECT id FROM projects").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        repo.conn.execute("INSERT INTO dependencies VALUES (?, 'a', 'ghost', 0)", (pid,))
    with pytest.raises(sqlite3.IntegrityError):
        repo.conn.execute(
            "INSERT INTO tasks VALUES (?, 'x', 'X', -1, '', 3, NULL, 0, 9)", (pid,))
    with pytest.raises(sqlite3.IntegrityError):
        repo.conn.execute(
            "INSERT INTO tasks VALUES (?, 'x', 'X', 1, '', 9, NULL, 0, 9)", (pid,))
    repo.conn.rollback()


def test_data_survives_reopening(tmp_path, sample_project):
    path = str(tmp_path / "persist.db")
    with Repository(path) as r:
        r.save_project(sample_project)
    with Repository(path) as r:
        assert r.load_project(sample_project.name).tasks == sample_project.tasks
