from datetime import date

import pytest

from planner.graph import CycleError, MissingDependencyError
from planner.models import Project, Task, ValidationError
from planner.serialization import dump_json, load_json, project_from_dict, task_from_dict
from tests.conftest import T, make_project


@pytest.mark.parametrize("kwargs, message", [
    ({"id": "bad id"}, "invalid task id"),
    ({"id": ""}, "invalid task id"),
    ({"name": "  "}, "name"),
    ({"duration": -1}, "duration"),
    ({"duration": 1.5}, "duration"),
    ({"duration": True}, "duration"),
    ({"priority": 0}, "priority"),
    ({"priority": 6}, "priority"),
    ({"depends_on": ("x", "x")}, "duplicate"),
    ({"deadline": "2026-01-01"}, "deadline"),
])
def test_task_validation(kwargs, message):
    base = {"id": "t", "name": "Task", "duration": 1}
    with pytest.raises(ValidationError, match=message):
        Task(**{**base, **kwargs})


def test_project_add_rejects_cycles_and_rolls_back():
    p = make_project(T("a"), T("b", deps=["a"]))
    with pytest.raises(CycleError):
        p.replace(T("a", deps=["b"]))
    assert p.tasks["a"].depends_on == ()  # unchanged
    with pytest.raises(MissingDependencyError):
        p.add(T("c", deps=["nope"]))
    assert "c" not in p.tasks
    with pytest.raises(ValidationError, match="duplicate"):
        p.add(T("a"))


def test_remove_refuses_when_others_depend():
    p = make_project(T("a"), T("b", deps=["a"]))
    with pytest.raises(ValidationError, match="b depend"):
        p.remove("a")
    p.remove("b")
    p.remove("a")
    assert p.tasks == {}
    with pytest.raises(ValidationError):
        p.remove("a")


def test_project_validation():
    with pytest.raises(ValidationError):
        Project("", date(2026, 1, 1))
    with pytest.raises(ValidationError):
        Project("x", "2026-01-01")


def test_json_round_trip(sample_project, tmp_path):
    path = tmp_path / "p.json"
    path.write_text(dump_json(sample_project), encoding="utf-8")
    again = load_json(str(path))
    assert again.tasks == sample_project.tasks
    assert again.start == sample_project.start


def test_from_dict_is_forgiving_about_types():
    t = task_from_dict({"id": "a", "name": "A", "duration": "3", "priority": 2.0,
                        "depends_on": "x, y", "deadline": ""})
    assert t.duration == 3 and t.priority == 2 and t.depends_on == ("x", "y") and t.deadline is None


@pytest.mark.parametrize("data, message", [
    ({"name": "p", "start": "soon", "tasks": []}, "not a date"),
    ({"name": "p", "start": "2026-01-01", "tasks": {}}, "must be a list"),
    ({"name": "p", "start": "2026-01-01", "tasks": [1]}, "object"),
    ({"name": "p", "start": "2026-01-01", "tasks": [{"id": "a", "name": "A", "duration": "x"}]}, "whole number"),
    ([], "object"),
])
def test_from_dict_errors(data, message):
    with pytest.raises(ValidationError, match=message):
        project_from_dict(data)


def test_load_json_invalid(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValidationError, match="invalid JSON"):
        load_json(str(path))
