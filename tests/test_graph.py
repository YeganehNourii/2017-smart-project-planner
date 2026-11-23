import pytest

from planner.graph import CycleError, MissingDependencyError, topological_sort
from planner.models import ValidationError
from tests.conftest import T


def assert_valid_order(order, tasks):
    pos = {tid: i for i, tid in enumerate(order)}
    assert sorted(order) == sorted(t.id for t in tasks)
    for t in tasks:
        for d in t.depends_on:
            assert pos[d] < pos[t.id], f"{d} must come before {t.id}"


def test_empty():
    assert topological_sort([]) == []


def test_single_task():
    assert topological_sort([T("a")]) == ["a"]


def test_chain_given_backwards():
    tasks = [T("c", deps=["b"]), T("b", deps=["a"]), T("a")]
    assert topological_sort(tasks) == ["a", "b", "c"]


def test_diamond():
    tasks = [T("a"), T("b", deps=["a"]), T("c", deps=["a"]), T("d", deps=["b", "c"])]
    order = topological_sort(tasks)
    assert_valid_order(order, tasks)
    assert order == ["a", "b", "c", "d"]


def test_independent_tasks_keep_input_order():
    tasks = [T("z"), T("m"), T("a")]
    assert topological_sort(tasks) == ["z", "m", "a"]


def test_disconnected_components():
    tasks = [T("x"), T("y", deps=["x"]), T("p"), T("q", deps=["p"])]
    assert_valid_order(topological_sort(tasks), tasks)


def test_missing_dependency():
    with pytest.raises(MissingDependencyError) as exc:
        topological_sort([T("a", deps=["ghost"])])
    assert exc.value.task_id == "a" and exc.value.missing == "ghost"
    assert "ghost" in str(exc.value)


def test_duplicate_ids():
    with pytest.raises(ValidationError, match="duplicate"):
        topological_sort([T("a"), T("a")])


def test_self_loop_is_a_cycle():
    with pytest.raises(CycleError) as exc:
        topological_sort([T("a", deps=["a"])])
    assert exc.value.cycle == ["a", "a"]


def test_two_node_cycle():
    with pytest.raises(CycleError) as exc:
        topological_sort([T("a", deps=["b"]), T("b", deps=["a"])])
    cyc = exc.value.cycle
    assert cyc[0] == cyc[-1] and set(cyc) == {"a", "b"}


def test_cycle_message_is_in_execution_order():
    # a needs c, b needs a, c needs b: c → b → a → c can never start.
    tasks = [T("start"), T("a", deps=["start", "c"]), T("b", deps=["a"]), T("c", deps=["b"])]
    with pytest.raises(CycleError) as exc:
        topological_sort(tasks)
    cyc = exc.value.cycle
    assert len(cyc) == 4 and cyc[0] == cyc[-1]
    assert set(cyc) == {"a", "b", "c"}
    # Each task in the message must be a dependency of the next one.
    by_id = {t.id: t for t in tasks}
    for before, after in zip(cyc, cyc[1:]):
        assert before in by_id[after].depends_on
    assert "→" in str(exc.value)


def test_cycle_downstream_of_valid_part_is_found():
    tasks = [T("a"), T("b", deps=["a"]), T("x", deps=["b", "y"]), T("y", deps=["x"]), T("z", deps=["y"])]
    with pytest.raises(CycleError) as exc:
        topological_sort(tasks)
    assert set(exc.value.cycle) == {"x", "y"}


def test_large_chain_is_not_recursive():
    # 5000 tasks in a line: an iterative algorithm must not hit recursion limits.
    tasks = [T("t0")] + [T(f"t{i}", deps=[f"t{i - 1}"]) for i in range(1, 5000)]
    assert topological_sort(list(reversed(tasks)))[-1] == "t4999"
    tasks.append(T("t0x", deps=["t4999"]))
    cyclic = [T("t0", deps=["t4999"])] + tasks[1:]
    with pytest.raises(CycleError) as exc:
        topological_sort(cyclic)
    assert len(exc.value.cycle) == 5001
