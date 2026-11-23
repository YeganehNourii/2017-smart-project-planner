"""Critical path method (CPM).

Times are whole days counted from the project start. A task occupies the
days ``[es, ef)``; a milestone (duration 0) has ``es == ef``.

* Forward pass, in topological order: ``es = max(ef of dependencies)``,
  ``ef = es + duration``. Project duration = max ef.
* Backward pass, in reverse order: ``lf = min(ls of dependents)`` (or the
  project duration for tasks nothing depends on), ``ls = lf - duration``.
* ``slack = ls - es``. Tasks with zero slack are critical.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .graph import successors_map, topological_sort
from .models import Project


@dataclass(frozen=True)
class TaskSchedule:
    task_id: str
    es: int
    ef: int
    ls: int
    lf: int
    start_date: date
    finish_date: date  # last day of work (inclusive); for milestones, the day itself
    deadline: date | None

    @property
    def slack(self) -> int:
        return self.ls - self.es

    @property
    def critical(self) -> bool:
        return self.slack == 0

    @property
    def late(self) -> bool:
        return self.deadline is not None and self.finish_date > self.deadline

    @property
    def days_late(self) -> int:
        return (self.finish_date - self.deadline).days if self.late else 0


@dataclass(frozen=True)
class CPMResult:
    order: list[str]
    schedule: dict[str, TaskSchedule]
    critical_path: list[str]
    duration: int
    end_date: date

    @property
    def critical_ids(self) -> set[str]:
        return {tid for tid, s in self.schedule.items() if s.critical}

    @property
    def late_tasks(self) -> list[str]:
        return [tid for tid in self.order if self.schedule[tid].late]


def _day_of(start: date, es: int, ef: int) -> tuple[date, date]:
    """Calendar (start_date, finish_date), both inclusive.

    A task with duration d works on days es .. ef-1. A milestone takes no
    time: it happens at the end of the day its dependencies finish (day
    es-1), or on the start day if it has no dependencies.
    """
    if ef == es:
        day = start + timedelta(days=max(es - 1, 0))
        return day, day
    return start + timedelta(days=es), start + timedelta(days=ef - 1)


def critical_path(project: Project) -> CPMResult:
    tasks = project.tasks
    order = topological_sort(tasks.values())
    succ = successors_map(tasks)

    es: dict[str, int] = {}
    ef: dict[str, int] = {}
    for tid in order:
        task = tasks[tid]
        es[tid] = max((ef[d] for d in task.depends_on), default=0)
        ef[tid] = es[tid] + task.duration
    duration = max(ef.values(), default=0)

    ls: dict[str, int] = {}
    lf: dict[str, int] = {}
    for tid in reversed(order):
        lf[tid] = min((ls[s] for s in succ[tid]), default=duration)
        ls[tid] = lf[tid] - tasks[tid].duration

    schedule = {}
    for tid in order:
        start_date, finish_date = _day_of(project.start, es[tid], ef[tid])
        schedule[tid] = TaskSchedule(
            task_id=tid,
            es=es[tid],
            ef=ef[tid],
            ls=ls[tid],
            lf=lf[tid],
            start_date=start_date,
            finish_date=finish_date,
            deadline=tasks[tid].deadline,
        )

    return CPMResult(
        order=order,
        schedule=schedule,
        critical_path=_longest_critical_chain(order, tasks, succ, schedule),
        duration=duration,
        end_date=project.start + timedelta(days=max(duration - 1, 0)),
    )


def _longest_critical_chain(order, tasks, succ, schedule) -> list[str]:
    """One chain of critical tasks from a start task to an end task.

    Every task with zero slack is critical, but when there are parallel
    critical branches we still want one readable path. We follow "tight"
    edges (successor starts exactly when this task ends) between critical
    tasks, preferring the chain that covers the most tasks, then input order.
    """
    critical = [tid for tid in order if schedule[tid].critical]
    if not critical:
        return []
    best_len: dict[str, int] = {}
    best_next: dict[str, str | None] = {}
    for tid in reversed(critical):
        best_len[tid], best_next[tid] = 1, None
        for s in succ[tid]:
            if s in best_len and schedule[s].es == schedule[tid].ef:
                if best_len[s] + 1 > best_len[tid]:
                    best_len[tid], best_next[tid] = best_len[s] + 1, s
    starts = [tid for tid in critical if schedule[tid].es == 0]
    node: str | None = max(starts, key=lambda t: best_len[t]) if starts else critical[0]
    chain = []
    while node is not None:
        chain.append(node)
        node = best_next[node]
    return chain
