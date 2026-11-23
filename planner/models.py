"""Domain model: a Task and a Project that owns tasks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Iterable

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")
MAX_DURATION = 3650


class ValidationError(ValueError):
    """Raised when a task or project is not valid."""


@dataclass(frozen=True)
class Task:
    id: str
    name: str
    duration: int  # whole days; 0 means a milestone
    owner: str = ""
    priority: int = 3  # 1 = highest, 5 = lowest
    deadline: date | None = None
    depends_on: tuple[str, ...] = ()
    done: bool = False

    def __post_init__(self) -> None:
        # Normalise lists to tuples so a Task is immutable and hashable.
        object.__setattr__(self, "depends_on", tuple(self.depends_on))
        if not isinstance(self.id, str) or not ID_PATTERN.match(self.id):
            raise ValidationError(
                f"invalid task id {self.id!r}: use 1-40 letters, digits, '-', '_' or '.'"
            )
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError(f"task {self.id!r}: name must not be empty")
        if isinstance(self.duration, bool) or not isinstance(self.duration, int):
            raise ValidationError(f"task {self.id!r}: duration must be a whole number of days")
        if not 0 <= self.duration <= MAX_DURATION:
            raise ValidationError(f"task {self.id!r}: duration must be between 0 and {MAX_DURATION}")
        if isinstance(self.priority, bool) or self.priority not in (1, 2, 3, 4, 5):
            raise ValidationError(f"task {self.id!r}: priority must be 1 (highest) to 5 (lowest)")
        if self.deadline is not None and not isinstance(self.deadline, date):
            raise ValidationError(f"task {self.id!r}: deadline must be a date")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValidationError(f"task {self.id!r}: duplicate dependency")

    @property
    def is_milestone(self) -> bool:
        return self.duration == 0

    def with_changes(self, **changes) -> "Task":
        return replace(self, **changes)


@dataclass
class Project:
    name: str
    start: date
    tasks: dict[str, Task] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("project name must not be empty")
        if not isinstance(self.start, date):
            raise ValidationError("project start must be a date")

    @classmethod
    def from_tasks(cls, name: str, start: date, tasks: Iterable[Task]) -> "Project":
        project = cls(name, start)
        for task in tasks:
            project.add(task, validate=False)
        project.validate()
        return project

    def add(self, task: Task, validate: bool = True) -> None:
        if task.id in self.tasks:
            raise ValidationError(f"duplicate task id {task.id!r}")
        self.tasks[task.id] = task
        if validate:
            try:
                self.validate()
            except ValidationError:
                del self.tasks[task.id]
                raise

    def replace(self, task: Task) -> None:
        if task.id not in self.tasks:
            raise ValidationError(f"no task with id {task.id!r}")
        old = self.tasks[task.id]
        self.tasks[task.id] = task
        try:
            self.validate()
        except ValidationError:
            self.tasks[task.id] = old
            raise

    def get(self, task_id: str) -> Task:
        try:
            return self.tasks[task_id]
        except KeyError:
            raise ValidationError(f"no task with id {task_id!r}") from None

    def dependents_of(self, task_id: str) -> list[str]:
        return [t.id for t in self.tasks.values() if task_id in t.depends_on]

    def remove(self, task_id: str) -> None:
        self.get(task_id)
        users = self.dependents_of(task_id)
        if users:
            raise ValidationError(
                f"cannot delete {task_id!r}: {', '.join(users)} depend(s) on it"
            )
        del self.tasks[task_id]

    def validate(self) -> list[str]:
        """Checks dependencies exist and there are no cycles.
        Returns the topological order; raises ValidationError otherwise."""
        from .graph import topological_sort  # local import: graph imports models

        return topological_sort(self.tasks.values())
