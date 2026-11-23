"""SQLite storage: a small data-access layer (Repository pattern).

Three tables. Foreign keys keep the data consistent even if someone edits
the database by hand:

    projects(id, name, start_date)
    tasks(project_id, key, name, duration, owner, priority, deadline, done, position)
    dependencies(project_id, task_key, depends_on, seq)

Every write runs inside a transaction, so a failed save changes nothing.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from .models import Project, Task, ValidationError

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    start_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key        TEXT    NOT NULL,
    name       TEXT    NOT NULL,
    duration   INTEGER NOT NULL CHECK (duration >= 0),
    owner      TEXT    NOT NULL DEFAULT '',
    priority   INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    deadline   TEXT,
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    position   INTEGER NOT NULL,
    PRIMARY KEY (project_id, key)
);
CREATE TABLE IF NOT EXISTS dependencies (
    project_id INTEGER NOT NULL,
    task_key   TEXT    NOT NULL,
    depends_on TEXT    NOT NULL,
    seq        INTEGER NOT NULL,  -- keeps the order the dependencies were listed in
    PRIMARY KEY (project_id, task_key, depends_on),
    FOREIGN KEY (project_id, task_key)   REFERENCES tasks(project_id, key) ON DELETE CASCADE,
    FOREIGN KEY (project_id, depends_on) REFERENCES tasks(project_id, key) ON DELETE CASCADE
);
"""


class NotFoundError(LookupError):
    pass


class Repository:
    def __init__(self, path: str = "planner.db") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    # -- context manager --------------------------------------------------
    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Repository":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- projects ---------------------------------------------------------
    def list_projects(self) -> list[str]:
        rows = self.conn.execute("SELECT name FROM projects ORDER BY name")
        return [r[0] for r in rows]

    def save_project(self, project: Project) -> None:
        """Insert or fully replace a project and its tasks."""
        project.validate()
        with self.conn:  # one transaction: commit on success, rollback on error
            row = self.conn.execute(
                "SELECT id FROM projects WHERE name = ?", (project.name,)
            ).fetchone()
            if row is None:
                pid = self.conn.execute(
                    "INSERT INTO projects (name, start_date) VALUES (?, ?)",
                    (project.name, project.start.isoformat()),
                ).lastrowid
            else:
                pid = row[0]
                self.conn.execute(
                    "UPDATE projects SET start_date = ? WHERE id = ?",
                    (project.start.isoformat(), pid),
                )
                self.conn.execute("DELETE FROM tasks WHERE project_id = ?", (pid,))
            self.conn.executemany(
                "INSERT INTO tasks (project_id, key, name, duration, owner, priority,"
                " deadline, done, position) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        pid, t.id, t.name, t.duration, t.owner, t.priority,
                        t.deadline.isoformat() if t.deadline else None, int(t.done), i,
                    )
                    for i, t in enumerate(project.tasks.values())
                ],
            )
            self.conn.executemany(
                "INSERT INTO dependencies (project_id, task_key, depends_on, seq)"
                " VALUES (?, ?, ?, ?)",
                [
                    (pid, t.id, d, i)
                    for t in project.tasks.values()
                    for i, d in enumerate(t.depends_on)
                ],
            )

    def load_project(self, name: str) -> Project:
        row = self.conn.execute(
            "SELECT id, start_date FROM projects WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"no project named {name!r}")
        pid, start = row
        deps: dict[str, list[str]] = {}
        for task_key, dep in self.conn.execute(
            "SELECT task_key, depends_on FROM dependencies"
            " WHERE project_id = ? ORDER BY task_key, seq",
            (pid,),
        ):
            deps.setdefault(task_key, []).append(dep)
        tasks = [
            Task(
                id=key, name=tname, duration=duration, owner=owner, priority=priority,
                deadline=date.fromisoformat(deadline) if deadline else None,
                depends_on=tuple(deps.get(key, ())), done=bool(done),
            )
            for key, tname, duration, owner, priority, deadline, done in self.conn.execute(
                "SELECT key, name, duration, owner, priority, deadline, done"
                " FROM tasks WHERE project_id = ? ORDER BY position",
                (pid,),
            )
        ]
        return Project.from_tasks(name, date.fromisoformat(start), tasks)

    def delete_project(self, name: str) -> None:
        with self.conn:
            cur = self.conn.execute("DELETE FROM projects WHERE name = ?", (name,))
        if cur.rowcount == 0:
            raise NotFoundError(f"no project named {name!r}")

    # -- tasks (load, change with validation, save) ------------------------
    def add_task(self, project_name: str, task: Task) -> None:
        project = self.load_project(project_name)
        project.add(task)
        self.save_project(project)

    def set_done(self, project_name: str, task_id: str, done: bool = True) -> None:
        project = self.load_project(project_name)
        project.replace(project.get(task_id).with_changes(done=done))
        self.save_project(project)

    def delete_task(self, project_name: str, task_id: str) -> None:
        project = self.load_project(project_name)
        project.remove(task_id)
        self.save_project(project)


__all__ = ["NotFoundError", "Repository", "SCHEMA", "ValidationError"]
