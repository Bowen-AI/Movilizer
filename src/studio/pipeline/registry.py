from __future__ import annotations

from typing import Any, Callable


class Registry:
    def __init__(self) -> None:
        self._items: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        self._items[name] = factory

    def get(self, name: str) -> Callable[..., Any]:
        if name not in self._items:
            raise KeyError(f"Registry item not found: {name}")
        return self._items[name]

    def names(self) -> list[str]:
        return sorted(self._items)
