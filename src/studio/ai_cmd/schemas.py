from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Action:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionPlan:
    request: str
    backend: str
    context: dict[str, Any]
    dry_run: bool
    actions: list[Action] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "backend": self.backend,
            "context": self.context,
            "dry_run": self.dry_run,
            "actions": [asdict(a) for a in self.actions],
        }
