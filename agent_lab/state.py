from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunState:
    """Mutable container for a pipeline run, persisted as JSON."""

    brief: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    transcript: list[str] = field(default_factory=list)
    status: str = "running"

    def save(self, path: Path) -> None:
        data = {
            "brief": self.brief,
            "artifacts": self.artifacts,
            "transcript": self.transcript,
            "status": self.status,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RunState:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            brief=data["brief"],
            artifacts=data.get("artifacts", []),
            transcript=data.get("transcript", []),
            status=data.get("status", "running"),
        )
