from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class Task:
    id: int
    text: str
    done: bool = False
    created_at: str = ""
    done_at: str = ""
    priority: str = ""
    due: str = ""
    tags: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["tags"] is None:
            d["tags"] = []
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Task":
        return Task(
            id=int(d.get("id")),
            text=str(d.get("text", "")),
            done=bool(d.get("done", False)),
            created_at=str(d.get("created_at", "")),
            done_at=str(d.get("done_at", "")),
            priority=str(d.get("priority", "")),
            due=str(d.get("due", "")),
            tags=list(d.get("tags") or []),
        )
