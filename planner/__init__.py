"""Smart Project Planner: pick the next task and draw the timeline.

The scheduling core (heap, topological sort, critical path method) uses only
the Python standard library, so it also runs in the browser via Pyodide.
"""
from .cpm import CPMResult, TaskSchedule, critical_path
from .graph import CycleError, MissingDependencyError, topological_sort
from .heap import BinaryHeap
from .models import Project, Task, ValidationError
from .scheduler import Recommendation, next_tasks

__all__ = [
    "BinaryHeap",
    "CPMResult",
    "CycleError",
    "MissingDependencyError",
    "Project",
    "Recommendation",
    "Task",
    "TaskSchedule",
    "ValidationError",
    "critical_path",
    "next_tasks",
    "topological_sort",
]
__version__ = "1.0.0"
