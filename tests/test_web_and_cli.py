import json

from planner import cli
from planner.gantt import gantt_figure, gantt_html, gantt_svg
from planner.cpm import critical_path
from planner.web import analyse
from tests.conftest import SAMPLE


def test_analyse_sample():
    out = json.loads(analyse(SAMPLE.read_text(encoding="utf-8")))
    assert out["ok"] is True
    assert out["project"]["duration"] == 19
    assert out["critical_path"][0] == "req" and out["critical_path"][-1] == "demo"
    assert [n["id"] for n in out["next"]] == ["uml", "mock"]
    assert out["warnings"] == []
    rows = {r["id"]: r for r in out["schedule"]}
    assert rows["api"]["critical"] and rows["docs"]["slack"] == 6
    names = [t["name"] for t in out["figure"]["data"]]
    assert {"Critical path", "Has slack", "Done", "Milestone", "Deadline"} <= set(names)


def test_analyse_reports_errors_instead_of_raising():
    cyc = {"name": "p", "start": "2026-01-01",
           "tasks": [{"id": "a", "name": "A", "duration": 1, "depends_on": ["b"]},
                     {"id": "b", "name": "B", "duration": 1, "depends_on": ["a"]}]}
    out = json.loads(analyse(json.dumps(cyc)))
    assert out["ok"] is False and "cycle" in out["error"]
    assert json.loads(analyse("{oops"))["ok"] is False


def test_analyse_warns_about_late_tasks():
    p = {"name": "p", "start": "2026-01-01",
         "tasks": [{"id": "a", "name": "Write", "duration": 5, "deadline": "2026-01-02"}]}
    out = json.loads(analyse(json.dumps(p)))
    assert out["warnings"] == ["Write is planned to finish 3 day(s) after its deadline"]


def test_gantt_outputs(sample_project):
    r = critical_path(sample_project)
    fig = gantt_figure(sample_project, r)
    bars = [t for t in fig["data"] if t["type"] == "bar"]
    assert sum(len(t["y"]) for t in bars) == 10  # 11 tasks minus 1 milestone
    assert fig["layout"]["xaxis"]["type"] == "date"
    json.dumps(fig)  # must be JSON-serialisable for Plotly.js
    assert gantt_svg(sample_project, r).startswith("<svg")
    assert "Plotly.newPlot" in gantt_html(sample_project, r)


def test_cli_end_to_end(tmp_path, capsys):
    db = str(tmp_path / "cli.db")
    name = "Campus study-room app"
    assert cli.main(["--db", db, "import", str(SAMPLE)]) == 0
    assert cli.main(["--db", db, "projects"]) == 0
    assert cli.main(["--db", db, "show", name]) == 0
    assert "Critical path: req → uml → db → api → integ → test → demo" in capsys.readouterr().out

    assert cli.main(["--db", db, "next", name, "--limit", "1"]) == 0
    assert "1. uml" in capsys.readouterr().out

    assert cli.main(["--db", db, "done", name, "uml"]) == 0
    assert cli.main(["--db", db, "add", name, "slides", "Demo slides", "--duration", "1",
                     "--owner", "Sara", "--after", "front", "--deadline", "2026-03-20"]) == 0
    assert cli.main(["--db", db, "export", name]) == 0
    exported = json.loads(capsys.readouterr().out.split("\n", 2)[-1])
    assert exported["tasks"][-1]["id"] == "slides"

    out = tmp_path / "g.svg"
    assert cli.main(["--db", db, "gantt", name, "--out", str(out)]) == 0
    assert out.read_text().startswith("<svg")

    assert cli.main(["--db", db, "init", "Empty", "--start", "2026-05-01"]) == 0
    assert cli.main(["--db", db, "next", "Empty"]) == 0
    assert "Nothing to do" in capsys.readouterr().out


def test_cli_errors(tmp_path, capsys):
    db = str(tmp_path / "cli.db")
    assert cli.main(["--db", db, "show", "nope"]) == 1
    assert "no project named" in capsys.readouterr().err
    cli.main(["--db", db, "import", str(SAMPLE)])
    assert cli.main(["--db", db, "add", "Campus study-room app", "x", "X", "--after", "ghost"]) == 1
    assert cli.main(["--db", db, "delete", "Campus study-room app", "req"]) == 1
    assert "depend" in capsys.readouterr().err
