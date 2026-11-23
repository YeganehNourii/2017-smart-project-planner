from datetime import date

from planner.cpm import critical_path
from tests.conftest import T, make_project


def test_textbook_example(textbook):
    r = critical_path(textbook)
    s = r.schedule
    assert (s["A"].es, s["A"].ef, s["A"].ls, s["A"].lf) == (0, 3, 0, 3)
    assert (s["B"].es, s["B"].ef, s["B"].ls, s["B"].lf) == (3, 5, 5, 7)
    assert (s["C"].es, s["C"].ef, s["C"].ls, s["C"].lf) == (3, 7, 3, 7)
    assert (s["D"].es, s["D"].ef, s["D"].ls, s["D"].lf) == (7, 9, 7, 9)
    assert s["B"].slack == 2
    assert r.critical_ids == {"A", "C", "D"}
    assert r.critical_path == ["A", "C", "D"]
    assert r.duration == 9


def test_calendar_dates(textbook):
    r = critical_path(textbook)  # starts Monday 2026-03-02
    assert r.schedule["A"].start_date == date(2026, 3, 2)
    assert r.schedule["A"].finish_date == date(2026, 3, 4)  # 3 days: 2, 3, 4
    assert r.schedule["C"].start_date == date(2026, 3, 5)
    assert r.end_date == date(2026, 3, 10)


def test_empty_project():
    r = critical_path(make_project())
    assert r.order == [] and r.duration == 0 and r.critical_path == []
    assert r.end_date == date(2026, 3, 2)


def test_single_task_is_critical():
    r = critical_path(make_project(T("only", 4)))
    assert r.critical_path == ["only"] and r.duration == 4


def test_independent_tasks_longest_is_critical():
    r = critical_path(make_project(T("short", 2), T("long", 5)))
    assert r.schedule["short"].slack == 3
    assert r.critical_ids == {"long"}


def test_parallel_critical_branches():
    p = make_project(T("a", 2), T("b", 3, ["a"]), T("c", 3, ["a"]), T("d", 1, ["b", "c"]))
    r = critical_path(p)
    assert r.critical_ids == {"a", "b", "c", "d"}
    assert r.critical_path in (["a", "b", "d"], ["a", "c", "d"])


def test_milestones_take_no_time():
    p = make_project(T("kickoff", 0), T("work", 4, ["kickoff"]), T("release", 0, ["work"]))
    r = critical_path(p)
    assert r.schedule["kickoff"].es == r.schedule["kickoff"].ef == 0
    assert r.schedule["release"].es == 4
    assert r.duration == 4
    # A milestone happens at the end of the day its dependencies finish.
    assert r.schedule["release"].finish_date == r.schedule["work"].finish_date == r.end_date
    assert r.schedule["kickoff"].start_date == date(2026, 3, 2)
    assert r.critical_path == ["kickoff", "work", "release"]


def test_all_zero_durations():
    r = critical_path(make_project(T("a", 0), T("b", 0, ["a"])))
    assert r.duration == 0 and r.critical_ids == {"a", "b"}


def test_slack_is_never_negative_and_ls_ge_es(textbook):
    r = critical_path(textbook)
    for s in r.schedule.values():
        assert s.slack >= 0 and s.ls >= s.es and s.lf == s.ls + (s.ef - s.es)


def test_deadline_lateness():
    p = make_project(
        T("a", 3, deadline=date(2026, 3, 4)),           # finishes 03-04: on time
        T("b", 3, ["a"], deadline=date(2026, 3, 6)),     # finishes 03-07: 1 day late
        T("m", 0, ["b"], deadline=date(2026, 3, 7)),     # milestone 03-07: on time
    )
    r = critical_path(p)
    assert not r.schedule["a"].late
    assert r.schedule["b"].late and r.schedule["b"].days_late == 1
    assert not r.schedule["m"].late
    assert r.late_tasks == ["b"]


def test_done_tasks_still_count_in_the_plan(textbook):
    done = make_project(*[t.with_changes(done=True) for t in textbook.tasks.values()])
    assert critical_path(done).duration == critical_path(textbook).duration


def test_sample_project(sample_project):
    r = critical_path(sample_project)
    assert r.critical_path == ["req", "uml", "db", "api", "integ", "test", "demo"]
    assert r.duration == 19
    assert r.end_date == date(2026, 3, 20)
    assert r.schedule["docs"].slack == 6
    assert r.late_tasks == []
