"""Dependency graph algorithms: topological sort with cycle detection."""
from __future__ import annotations

from typing import Iterable

from .heap import BinaryHeap
from .models import Task, ValidationError


class MissingDependencyError(ValidationError):
    def __init__(self, task_id: str, missing: str) -> None:
        self.task_id = task_id
        self.missing = missing
        super().__init__(f"task {task_id!r} depends on unknown task {missing!r}")


class CycleError(ValidationError):
    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__("dependency cycle: " + " → ".join(cycle))


def successors_map(tasks: dict[str, Task]) -> dict[str, list[str]]:
    """Maps each task id to the ids of tasks that depend on it."""
    succ: dict[str, list[str]] = {tid: [] for tid in tasks}
    for task in tasks.values():
        for dep in task.depends_on:
            succ[dep].append(task.id)
    return succ


def topological_sort(tasks: Iterable[Task]) -> list[str]:
    """Kahn's algorithm. Returns task ids so that every task comes after all
    of its dependencies.

    Among tasks that are ready at the same time, the one that appears first
    in the input comes first (a heap keyed by input position), so the
    result is deterministic. Runs in O((V + E) log V).

    Raises MissingDependencyError or CycleError.
    """
    by_id: dict[str, Task] = {}
    position: dict[str, int] = {}
    for i, task in enumerate(tasks):
        if task.id in by_id:
            raise ValidationError(f"duplicate task id {task.id!r}")
        by_id[task.id] = task
        position[task.id] = i

    for task in by_id.values():
        for dep in task.depends_on:
            if dep not in by_id:
                raise MissingDependencyError(task.id, dep)

    indegree = {tid: len(t.depends_on) for tid, t in by_id.items()}
    succ = successors_map(by_id)

    ready = BinaryHeap.from_items((tid, position[tid]) for tid, d in indegree.items() if d == 0)
    order: list[str] = []
    while ready:
        tid = ready.pop()
        order.append(tid)
        for nxt in succ[tid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.push(nxt, position[nxt])

    if len(order) != len(by_id):
        remaining = [tid for tid in by_id if indegree[tid] > 0]
        raise CycleError(find_cycle(by_id, remaining))
    return order


def find_cycle(by_id: dict[str, Task], candidates: list[str]) -> list[str]:
    """Finds one cycle with an iterative depth-first search (white/grey/black
    colouring) and returns it as [a, b, ..., a]. A grey node seen again
    means we followed edges back into the current path."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {tid: WHITE for tid in by_id}
    for start in candidates:
        if colour[start] != WHITE:
            continue
        path: list[str] = [start]
        colour[start] = GREY
        stack = [iter(by_id[start].depends_on)]
        while stack:
            dep = next(stack[-1], None)
            if dep is None:
                colour[path.pop()] = BLACK
                stack.pop()
            elif colour[dep] == GREY:
                # dep -> ... -> path[-1] -> dep, written in "depends on" order;
                # reverse it so it reads in execution order.
                cycle = path[path.index(dep):] + [dep]
                return list(reversed(cycle))
            elif colour[dep] == WHITE:
                colour[dep] = GREY
                path.append(dep)
                stack.append(iter(by_id[dep].depends_on))
    raise AssertionError("find_cycle called on an acyclic graph")  # pragma: no cover
