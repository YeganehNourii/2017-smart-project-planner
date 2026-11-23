"""Gantt chart output.

``gantt_figure`` returns a Plotly figure as a plain dict (no plotly import),
so the same code feeds Plotly.js in the browser and the HTML export.
``gantt_svg`` draws a static SVG used for the README screenshot.
"""
from __future__ import annotations

import html
import json
from datetime import timedelta

from .cpm import CPMResult
from .models import Project

DAY_MS = 86_400_000
COLORS = {"critical": "#d1495b", "normal": "#3a7ca5", "done": "#a7b0ba", "deadline": "#1f2933"}


def _rows(project: Project, result: CPMResult):
    for tid in result.order:
        task = project.tasks[tid]
        s = result.schedule[tid]
        kind = "done" if task.done else ("critical" if s.critical else "normal")
        yield task, s, kind


def _label(task) -> str:
    return f"{task.name} ({task.owner})" if task.owner else task.name


def gantt_figure(project: Project, result: CPMResult) -> dict:
    labels = [_label(t) for t, _, _ in _rows(project, result)]
    traces = []
    names = {"critical": "Critical path", "normal": "Has slack", "done": "Done"}
    for kind in ("critical", "normal", "done"):
        rows = [(t, s) for t, s, k in _rows(project, result) if k == kind and not t.is_milestone]
        if not rows:
            continue
        traces.append({
            "type": "bar",
            "orientation": "h",
            "name": names[kind],
            "y": [_label(t) for t, _ in rows],
            "base": [s.start_date.isoformat() for _, s in rows],
            "x": [t.duration * DAY_MS for t, _ in rows],
            "marker": {"color": COLORS[kind]},
            "customdata": [
                [t.id, s.start_date.isoformat(), s.finish_date.isoformat(), s.slack]
                for t, s in rows
            ],
            "hovertemplate": "<b>%{y}</b><br>%{customdata[1]} → %{customdata[2]}"
                             "<br>slack: %{customdata[3]} day(s)<extra>%{customdata[0]}</extra>",
        })
    milestones = [(t, s, k) for t, s, k in _rows(project, result) if t.is_milestone]
    if milestones:
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "name": "Milestone",
            "y": [_label(t) for t, _, _ in milestones],
            # Drawn on the boundary where its dependencies end (day es).
            "x": [(project.start + timedelta(days=s.es)).isoformat() for _, s, _ in milestones],
            "marker": {"symbol": "diamond", "size": 14,
                       "color": [COLORS[k] for _, _, k in milestones]},
            "hovertemplate": "<b>%{y}</b><br>%{x}<extra>milestone</extra>",
        })
    deadlines = [(t, s) for t, s, _ in _rows(project, result) if s.deadline]
    if deadlines:
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "name": "Deadline",
            "y": [_label(t) for t, _ in deadlines],
            # Deadline = end of that day, so draw it at the next midnight.
            "x": [(s.deadline + timedelta(days=1)).isoformat() for _, s in deadlines],
            "marker": {"symbol": "line-ns-open", "size": 18, "line": {"width": 3},
                       "color": ["#e85d04" if s.late else COLORS["deadline"] for _, s in deadlines]},
            "hovertemplate": "<b>%{y}</b><br>deadline<extra></extra>",
        })
    # Show the whole plan and every deadline, plus one day of padding.
    end = project.start + timedelta(days=result.duration)
    for _, s in deadlines:
        end = max(end, s.deadline + timedelta(days=1))
    end += timedelta(days=1)
    return {
        "data": traces,
        "layout": {
            "barmode": "overlay",
            "height": max(320, 34 * len(labels) + 120),
            "margin": {"l": 10, "r": 20, "t": 40, "b": 40},
            "title": {"text": f"{project.name}: {project.start.isoformat()} → "
                              f"{result.end_date.isoformat()} ({result.duration} days)"},
            "xaxis": {"type": "date", "range": [project.start.isoformat(), end.isoformat()],
                      "gridcolor": "rgba(128,128,128,0.2)"},
            "yaxis": {"categoryorder": "array", "categoryarray": labels,
                      "autorange": "reversed", "automargin": True},
            "legend": {"orientation": "h", "y": -0.12},
            "plot_bgcolor": "rgba(0,0,0,0)",
            "paper_bgcolor": "rgba(0,0,0,0)",
        },
    }


def gantt_html(project: Project, result: CPMResult) -> str:
    fig = json.dumps(gantt_figure(project, result))
    title = html.escape(project.name)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title} – Gantt</title>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
</head><body style="font-family:system-ui,sans-serif;margin:24px">
<div id="gantt"></div>
<script>const fig = {fig}; Plotly.newPlot("gantt", fig.data, fig.layout, {{responsive: true}});</script>
</body></html>
"""


def gantt_svg(project: Project, result: CPMResult, day_width: int = 22) -> str:
    """Static SVG Gantt chart (no JavaScript), e.g. for a README."""
    rows = list(_rows(project, result))
    row_h, top, pad = 28, 62, 16
    label_w = max([len(_label(t)) for t, _, _ in rows] + [10]) * 7 + 24
    days = max(result.duration, 1)
    for _, s, _ in rows:
        if s.deadline is not None:
            days = max(days, (s.deadline - project.start).days + 2)
    width = label_w + days * day_width + pad * 2
    height = top + len(rows) * row_h + 56
    x0 = pad + label_w
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{pad}" y="24" font-size="15" font-weight="600" fill="#1f2933">'
        f'{html.escape(project.name)}: {project.start.isoformat()} → {result.end_date.isoformat()} '
        f'({result.duration} days)</text>',
    ]
    for d in range(days + 1):
        x = x0 + d * day_width
        day = project.start + timedelta(days=d)
        weekly = day.weekday() == 0
        out.append(f'<line x1="{x}" y1="{top - 8}" x2="{x}" y2="{top + len(rows) * row_h}" '
                   f'stroke="{"#c5ccd3" if weekly else "#eef1f4"}"/>')
        if weekly and d < days:
            out.append(f'<text x="{x + 2}" y="{top - 14}" fill="#52606d">{day.strftime("%d %b")}</text>')
    for i, (task, s, kind) in enumerate(rows):
        y = top + i * row_h
        cy = y + row_h / 2
        out.append(f'<text x="{pad}" y="{cy + 4}" fill="#1f2933">{html.escape(_label(task))}</text>')
        color = COLORS[kind]
        if task.is_milestone:
            cx = x0 + s.es * day_width
            out.append(f'<path d="M{cx} {cy - 8} L{cx + 8} {cy} L{cx} {cy + 8} L{cx - 8} {cy} Z" fill="{color}"/>')
        else:
            out.append(f'<rect x="{x0 + s.es * day_width + 1}" y="{y + 5}" '
                       f'width="{task.duration * day_width - 2}" height="{row_h - 10}" rx="4" fill="{color}"/>')
        if s.deadline:
            dx = x0 + ((s.deadline - project.start).days + 1) * day_width
            if x0 <= dx <= x0 + days * day_width + day_width:
                stroke = "#e85d04" if s.late else COLORS["deadline"]
                out.append(f'<line x1="{dx}" y1="{y + 2}" x2="{dx}" y2="{y + row_h - 2}" '
                           f'stroke="{stroke}" stroke-width="3"/>')
    ly = top + len(rows) * row_h + 30
    legend = [("Critical path", COLORS["critical"]), ("Has slack", COLORS["normal"]),
              ("Done", COLORS["done"]), ("Deadline", COLORS["deadline"])]
    for j, (name, color) in enumerate(legend):
        lx = pad + j * 130
        out.append(f'<rect x="{lx}" y="{ly - 10}" width="14" height="12" rx="2" fill="{color}"/>')
        out.append(f'<text x="{lx + 20}" y="{ly}" fill="#1f2933">{name}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"
