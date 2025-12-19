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
    # Bug tracking fields
    bug_status: str = ""  # open, in-progress, fixed, closed
    bug_assignee: str = ""
    bug_severity: str = ""  # critical, high, medium, low
    bug_steps: str = ""  # steps to reproduce
    bug_environment: str = ""  # dev, staging, prod, etc.

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["tags"] is None:
            d["tags"] = []
        # Only include bug fields if they have values (backward compatibility)
        bug_fields = [
            "bug_status",
            "bug_assignee",
            "bug_severity",
            "bug_steps",
            "bug_environment",
        ]
        for field in bug_fields:
            if not d.get(field):
                d.pop(field, None)
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
            bug_status=str(d.get("bug_status", "")),
            bug_assignee=str(d.get("bug_assignee", "")),
            bug_severity=str(d.get("bug_severity", "")),
            bug_steps=str(d.get("bug_steps", "")),
            bug_environment=str(d.get("bug_environment", "")),
        )

    def is_bug(self) -> bool:
        """Check if this task is a bug (has bug fields or #bug tag)."""
        return (
            bool(self.bug_status)
            or bool(self.bug_assignee)
            or bool(self.bug_severity)
            or bool(self.bug_steps)
            or bool(self.bug_environment)
            or (self.tags and "bug" in [t.lower() for t in self.tags])
        )
