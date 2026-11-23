"""Picks the next tasks to work on, using the binary heap."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .cpm import CPMResult, TaskSchedule, critical_path
from .heap import BinaryHeap
from .models import Project, Task


@dataclass(frozen=True)
class Recommendation:
    task: Task
    schedule: TaskSchedule
    reasons: list[str] = field(default_factory=list)


def ready_tasks(project: Project) -> list[Task]:
    """Tasks that are not done and whose dependencies are all done."""
    tasks = project.tasks
    return [
        t
        for t in tasks.values()
        if not t.done and all(tasks[d].done for d in t.depends_on)
    ]


def urgency_key(task: Task, sched: TaskSchedule) -> tuple:
    """Smaller = more urgent: least slack, then the latest day it can start
    without delaying the project, then the nearest deadline, then priority."""
    deadline = sched.deadline.toordinal() if sched.deadline else date.max.toordinal()
    return (sched.slack, sched.ls, deadline, task.priority)


def next_tasks(
    project: Project,
    result: CPMResult | None = None,
    limit: int | None = 5,
    today: date | None = None,
) -> list[Recommendation]:
    """Ranks the tasks that can be started now, most urgent first."""
    if result is None:
        result = critical_path(project)
    heap: BinaryHeap[Task] = BinaryHeap.from_items(
        (t, urgency_key(t, result.schedule[t.id])) for t in ready_tasks(project)
    )
    recs: list[Recommendation] = []
    while heap and (limit is None or len(recs) < limit):
        task = heap.pop()
        sched = result.schedule[task.id]
        recs.append(Recommendation(task, sched, _reasons(task, sched, today)))
    return recs


def _reasons(task: Task, s: TaskSchedule, today: date | None) -> list[str]:
    reasons = []
    if s.critical:
        reasons.append("on the critical path: any delay moves the project end")
    else:
        reasons.append(f"{s.slack} day{'s' if s.slack != 1 else ''} of slack")
    if s.late:
        reasons.append(f"planned to finish {s.days_late} day(s) after its deadline")
    elif s.deadline is not None:
        reference = today or s.start_date
        left = (s.deadline - reference).days
        if today is not None and left < 0:
            reasons.append(f"deadline passed {-left} day(s) ago")
        else:
            reasons.append(f"deadline {s.deadline.isoformat()}")
    if task.priority <= 2:
        reasons.append(f"priority {task.priority}")
    return reasons
