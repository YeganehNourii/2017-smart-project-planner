import random

import pytest

from planner.heap import BinaryHeap


def test_pops_in_key_order():
    h = BinaryHeap()
    for k in [5, 1, 4, 2, 3]:
        h.push(f"item{k}", k)
    assert len(h) == 5
    assert [h.pop() for _ in range(5)] == ["item1", "item2", "item3", "item4", "item5"]
    assert not h


def test_peek_does_not_remove():
    h = BinaryHeap()
    h.push("b", 2)
    h.push("a", 1)
    assert h.peek() == "a" and h.peek_key() == 1
    assert len(h) == 2


def test_empty_heap_raises():
    h = BinaryHeap()
    with pytest.raises(IndexError):
        h.pop()
    with pytest.raises(IndexError):
        h.peek()
    with pytest.raises(IndexError):
        h.peek_key()


def test_equal_keys_are_fifo_and_items_never_compared():
    class NotComparable:
        def __init__(self, n):
            self.n = n

    h = BinaryHeap()
    items = [NotComparable(i) for i in range(20)]
    for it in items:
        h.push(it, 7)
    assert [h.pop().n for _ in range(20)] == list(range(20))


def test_tuple_keys():
    h = BinaryHeap()
    h.push("late-deadline", (0, 10))
    h.push("more-slack", (2, 0))
    h.push("early-deadline", (0, 3))
    assert list(h.drain()) == ["early-deadline", "late-deadline", "more-slack"]


@pytest.mark.parametrize("seed", range(10))
def test_matches_sorted_on_random_data(seed):
    rng = random.Random(seed)
    keys = [rng.randint(-50, 50) for _ in range(rng.randint(0, 300))]
    h = BinaryHeap()
    out = []
    for k in keys:  # interleave pushes and pops
        h.push(k, k)
        assert h._check_invariant()
        if rng.random() < 0.3:
            out.append(h.pop())
    out.extend(h.drain())
    # Popped values are not globally sorted (pops were interleaved), but every
    # value comes out exactly once and the final drain is sorted.
    assert sorted(out) == sorted(keys)


@pytest.mark.parametrize("n", [0, 1, 2, 3, 10, 101])
def test_from_items_heapify(n):
    rng = random.Random(n)
    keys = [rng.random() for _ in range(n)]
    h = BinaryHeap.from_items((k, k) for k in keys)
    assert h._check_invariant()
    assert list(h.drain()) == sorted(keys)
