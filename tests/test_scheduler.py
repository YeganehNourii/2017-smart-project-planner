from datetime import date

from planner.cpm import critical_path
from planner.scheduler import next_tasks, ready_tasks
from tests.conftest import T, make_project


def ids(recs):
    return [r.task.id for r in recs]


def test_only_tasks_with_finished_dependencies_are_ready(textbook):
    assert [t.id for t in ready_tasks(textbook)] == ["A"]
    p = make_project(*[t.with_changes(done=t.id == "A") for t in textbook.tasks.values()])
    assert [t.id for t in ready_tasks(p)] == ["B", "C"]


def test_critical_task_first(textbook):
    p = make_project(*[t.with_changes(done=t.id == "A") for t in textbook.tasks.values()])
    recs = next_tasks(p)
    assert ids(recs) == ["C", "B"]  # C has 0 slack, B has 2
    assert "critical path" in recs[0].reasons[0]
    assert recs[1].reasons[0] == "2 days of slack"


def test_ties_broken_by_deadline_then_priority():
    p = make_project(
        T("low", 2, priority=5),
        T("high", 2, priority=1),
        T("deadline", 2, priority=5, deadline=date(2026, 3, 3)),
    )
    # All three have zero slack and the same latest start.
    assert ids(next_tasks(p)) == ["deadline", "high", "low"]


def test_limit_and_nothing_to_do(textbook):
    assert len(next_tasks(textbook, limit=0)) == 0
    all_done = make_project(*[t.with_changes(done=True) for t in textbook.tasks.values()])
    assert next_tasks(all_done) == []
    assert next_tasks(make_project()) == []


def test_reuses_given_result(textbook):
    r = critical_path(textbook)
    assert ids(next_tasks(textbook, r)) == ["A"]


def test_reasons_mention_lateness_and_passed_deadlines():
    p = make_project(T("a", 5, deadline=date(2026, 3, 3), priority=1))
    rec = next_tasks(p)[0]
    assert any("after its deadline" in x for x in rec.reasons)
    assert "priority 1" in rec.reasons

    q = make_project(T("b", 1, deadline=date(2026, 3, 2)))
    rec = next_tasks(q, today=date(2026, 3, 5))[0]
    assert "deadline passed 3 day(s) ago" in rec.reasons


def test_sample_project_next(sample_project):
    assert ids(next_tasks(sample_project)) == ["uml", "mock"]


def test_none_limit_returns_all():
    p = make_project(*[T(f"t{i}", i + 1) for i in range(12)])
    recs = next_tasks(p, limit=None)
    assert len(recs) == 12
    assert ids(recs)[0] == "t11"  # the longest one is critical
