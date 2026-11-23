"""Entry point for the web demo (called from JavaScript through Pyodide).

``analyse`` takes a project as JSON text and returns everything the page
needs as JSON text, or ``{"ok": false, "error": "..."}`` for invalid input.
"""
from __future__ import annotations

import json
from datetime import date

from .cpm import critical_path
from .gantt import gantt_figure
from .models import ValidationError
from .scheduler import next_tasks
from .serialization import project_from_dict


def analyse(project_json: str, limit: int = 5, today: str | None = None) -> str:
    try:
        project = project_from_dict(json.loads(project_json))
        result = critical_path(project)
    except (ValidationError, json.JSONDecodeError) as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    today_date = date.fromisoformat(today) if today else None
    recs = next_tasks(project, result, limit=limit, today=today_date)
    schedule = []
    for tid in result.order:
        t, s = project.tasks[tid], result.schedule[tid]
        schedule.append({
            "id": t.id, "name": t.name, "owner": t.owner, "priority": t.priority,
            "duration": t.duration, "done": t.done, "depends_on": list(t.depends_on),
            "es": s.es, "ef": s.ef, "ls": s.ls, "lf": s.lf, "slack": s.slack,
            "critical": s.critical, "late": s.late, "days_late": s.days_late,
            "start": s.start_date.isoformat(), "finish": s.finish_date.isoformat(),
            "deadline": s.deadline.isoformat() if s.deadline else None,
        })
    return json.dumps({
        "ok": True,
        "project": {"name": project.name, "start": project.start.isoformat(),
                    "end": result.end_date.isoformat(), "duration": result.duration},
        "schedule": schedule,
        "critical_path": result.critical_path,
        "next": [{"id": r.task.id, "name": r.task.name, "owner": r.task.owner,
                  "reasons": r.reasons} for r in recs],
        "warnings": [
            f"{project.tasks[tid].name} is planned to finish "
            f"{result.schedule[tid].days_late} day(s) after its deadline"
            for tid in result.late_tasks
        ],
        "figure": gantt_figure(project, result),
    }, ensure_ascii=False)
