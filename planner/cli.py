"""Command-line interface: python -m planner --help"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from .cpm import critical_path
from .gantt import gantt_html, gantt_svg
from .models import Project, Task, ValidationError
from .scheduler import next_tasks
from .serialization import dump_json, load_json, parse_date
from .storage import NotFoundError, Repository


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="planner", description="Smart project planner")
    p.add_argument("--db", default="planner.db", help="SQLite file (default: planner.db)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="create an empty project")
    s.add_argument("project")
    s.add_argument("--start", default=date.today().isoformat(), help="YYYY-MM-DD")

    s = sub.add_parser("import", help="import (or replace) a project from JSON")
    s.add_argument("file")

    sub.add_parser("projects", help="list projects")

    s = sub.add_parser("show", help="tasks with schedule and slack")
    s.add_argument("project")

    s = sub.add_parser("next", help="what to work on next")
    s.add_argument("project")
    s.add_argument("--limit", type=int, default=5)

    s = sub.add_parser("add", help="add a task")
    s.add_argument("project")
    s.add_argument("id")
    s.add_argument("name")
    s.add_argument("--duration", type=int, default=1, help="days (0 = milestone)")
    s.add_argument("--owner", default="")
    s.add_argument("--priority", type=int, default=3, help="1 (highest) .. 5")
    s.add_argument("--deadline", help="YYYY-MM-DD")
    s.add_argument("--after", default="", help="comma-separated ids this task depends on")

    for name, help_text in (("done", "mark a task done"), ("undo", "mark a task not done"),
                            ("delete", "delete a task")):
        s = sub.add_parser(name, help=help_text)
        s.add_argument("project")
        s.add_argument("id")

    s = sub.add_parser("export", help="print a project as JSON")
    s.add_argument("project")

    s = sub.add_parser("gantt", help="write a Gantt chart (.html with Plotly, or .svg)")
    s.add_argument("project")
    s.add_argument("--out", default="gantt.html")
    return p


def cmd_show(project: Project) -> None:
    result = critical_path(project)
    print(f"{project.name}: {project.start} → {result.end_date} ({result.duration} days)")
    print(f"{'':2}{'ID':<10} {'TASK':<30} {'OWNER':<10} {'DAYS':>4} {'START':>10} "
          f"{'FINISH':>10} {'SLACK':>5}  DEADLINE")
    for tid in result.order:
        t, s = project.tasks[tid], result.schedule[tid]
        mark = "✓" if t.done else ("*" if s.critical else " ")
        deadline = ""
        if t.deadline:
            deadline = t.deadline.isoformat() + (f"  LATE by {s.days_late}d" if s.late else "")
        print(f"{mark:2}{t.id:<10} {t.name[:30]:<30} {t.owner[:10]:<10} {t.duration:>4} "
              f"{s.start_date.isoformat():>10} {s.finish_date.isoformat():>10} {s.slack:>5}  {deadline}")
    print("\n* critical  ✓ done")
    print("Critical path: " + " → ".join(result.critical_path))


def cmd_next(project: Project, limit: int) -> None:
    recs = next_tasks(project, limit=limit, today=date.today())
    if not recs:
        print("Nothing to do: every task is done or waiting on another task.")
        return
    for i, r in enumerate(recs, 1):
        owner = f" [{r.task.owner}]" if r.task.owner else ""
        print(f"{i}. {r.task.id}: {r.task.name}{owner}")
        print(f"   {'; '.join(r.reasons)}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with Repository(args.db) as repo:
            c = args.command
            if c == "init":
                repo.save_project(Project(args.project, parse_date(args.start, "--start")))
                print(f"Created project {args.project!r}")
            elif c == "import":
                project = load_json(args.file)
                repo.save_project(project)
                print(f"Imported {project.name!r} ({len(project.tasks)} tasks)")
            elif c == "projects":
                for name in repo.list_projects():
                    print(name)
            elif c == "show":
                cmd_show(repo.load_project(args.project))
            elif c == "next":
                cmd_next(repo.load_project(args.project), args.limit)
            elif c == "add":
                deps = tuple(x.strip() for x in args.after.split(",") if x.strip())
                task = Task(args.id, args.name, args.duration, args.owner, args.priority,
                            parse_date(args.deadline, "--deadline") if args.deadline else None,
                            deps)
                repo.add_task(args.project, task)
                print(f"Added {args.id!r}")
            elif c in ("done", "undo"):
                repo.set_done(args.project, args.id, c == "done")
                print(f"Marked {args.id!r} as {'done' if c == 'done' else 'not done'}")
            elif c == "delete":
                repo.delete_task(args.project, args.id)
                print(f"Deleted {args.id!r}")
            elif c == "export":
                sys.stdout.write(dump_json(repo.load_project(args.project)))
            elif c == "gantt":
                project = repo.load_project(args.project)
                result = critical_path(project)
                text = gantt_svg(project, result) if args.out.endswith(".svg") else gantt_html(project, result)
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"Wrote {args.out}")
    except (ValidationError, NotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
