"""A binary min-heap priority queue, written by hand (no ``heapq``).

The heap is a list where the children of index ``i`` are at ``2i + 1`` and
``2i + 2``. Every parent's key is <= its children's keys, so the smallest key
is always at index 0.

Each entry is stored as ``(key, counter, item)``. The counter grows with every
push, so two items with equal keys come out in insertion order (the heap is
*stable*), and items themselves are never compared.
"""
from __future__ import annotations

from typing import Any, Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")


class BinaryHeap(Generic[T]):
    def __init__(self) -> None:
        self._items: list[tuple[Any, int, T]] = []
        self._counter = 0

    # -- public API -------------------------------------------------------
    def push(self, item: T, key: Any) -> None:
        """Add ``item`` with priority ``key`` (smaller = sooner). O(log n)."""
        self._items.append((key, self._counter, item))
        self._counter += 1
        self._sift_up(len(self._items) - 1)

    def pop(self) -> T:
        """Remove and return the item with the smallest key. O(log n)."""
        if not self._items:
            raise IndexError("pop from empty heap")
        last = self._items.pop()
        if not self._items:
            return last[2]
        top = self._items[0]
        self._items[0] = last
        self._sift_down(0)
        return top[2]

    def peek(self) -> T:
        """Return the item with the smallest key without removing it. O(1)."""
        if not self._items:
            raise IndexError("peek at empty heap")
        return self._items[0][2]

    def peek_key(self) -> Any:
        if not self._items:
            raise IndexError("peek at empty heap")
        return self._items[0][0]

    @classmethod
    def from_items(cls, pairs: Iterable[tuple[T, Any]]) -> "BinaryHeap[T]":
        """Build a heap from ``(item, key)`` pairs in O(n) (bottom-up heapify)."""
        heap: BinaryHeap[T] = cls()
        for item, key in pairs:
            heap._items.append((key, heap._counter, item))
            heap._counter += 1
        for i in range(len(heap._items) // 2 - 1, -1, -1):
            heap._sift_down(i)
        return heap

    def drain(self) -> Iterator[T]:
        """Pop every item, smallest key first."""
        while self._items:
            yield self.pop()

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    # -- internals --------------------------------------------------------
    @staticmethod
    def _less(a: tuple[Any, int, T], b: tuple[Any, int, T]) -> bool:
        return (a[0], a[1]) < (b[0], b[1])

    def _sift_up(self, i: int) -> None:
        items = self._items
        while i > 0:
            parent = (i - 1) // 2
            if self._less(items[i], items[parent]):
                items[i], items[parent] = items[parent], items[i]
                i = parent
            else:
                break

    def _sift_down(self, i: int) -> None:
        items = self._items
        n = len(items)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            smallest = i
            if left < n and self._less(items[left], items[smallest]):
                smallest = left
            if right < n and self._less(items[right], items[smallest]):
                smallest = right
            if smallest == i:
                return
            items[i], items[smallest] = items[smallest], items[i]
            i = smallest

    def _check_invariant(self) -> bool:
        """True if every parent <= its children (used by the tests)."""
        items = self._items
        return all(
            not self._less(items[c], items[(c - 1) // 2]) for c in range(1, len(items))
        )
