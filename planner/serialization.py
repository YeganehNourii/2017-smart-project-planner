"""Convert projects to and from plain dicts / JSON."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from .models import Project, Task, ValidationError


def parse_date(value: Any, what: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(f"{what}: {value!r} is not a date (use YYYY-MM-DD)") from None


def task_from_dict(d: dict[str, Any]) -> Task:
    if not isinstance(d, dict):
        raise ValidationError("each task must be an object")
    deadline = d.get("deadline") or None
    deps = d.get("depends_on") or []
    if isinstance(deps, str):
        deps = [x.strip() for x in deps.split(",") if x.strip()]
    try:
        return Task(
            id=str(d.get("id", "")).strip(),
            name=str(d.get("name", "")).strip(),
            duration=_to_int(d.get("duration", 1), "duration"),
            owner=str(d.get("owner") or "").strip(),
            priority=_to_int(d.get("priority", 3), "priority"),
            deadline=parse_date(deadline, f"task {d.get('id')!r} deadline") if deadline else None,
            depends_on=tuple(str(x) for x in deps),
            done=bool(d.get("done", False)),
        )
    except TypeError as exc:  # e.g. unhashable values
        raise ValidationError(str(exc)) from None


def _to_int(value: Any, what: str) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"{what} must be a whole number")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    raise ValidationError(f"{what} must be a whole number, got {value!r}")


def task_to_dict(t: Task) -> dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "duration": t.duration,
        "owner": t.owner,
        "priority": t.priority,
        "deadline": t.deadline.isoformat() if t.deadline else None,
        "depends_on": list(t.depends_on),
        "done": t.done,
    }


def project_from_dict(d: dict[str, Any]) -> Project:
    if not isinstance(d, dict):
        raise ValidationError("project must be an object")
    tasks = d.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValidationError("'tasks' must be a list")
    return Project.from_tasks(
        str(d.get("name", "")).strip(),
        parse_date(d.get("start"), "project start"),
        [task_from_dict(t) for t in tasks],
    )


def project_to_dict(p: Project) -> dict[str, Any]:
    return {
        "name": p.name,
        "start": p.start.isoformat(),
        "tasks": [task_to_dict(t) for t in p.tasks.values()],
    }


def load_json(path: str) -> Project:
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path}: invalid JSON ({exc.msg} at line {exc.lineno})") from None
    return project_from_dict(data)


def dump_json(p: Project) -> str:
    return json.dumps(project_to_dict(p), indent=2, ensure_ascii=False) + "\n"
