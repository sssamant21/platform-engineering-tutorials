"""Offline enterprise rollout state machine. No cloud/Pulumi calls."""
from dataclasses import dataclass, field
ORDER = ("validate", "preview", "approve", "backup", "canary", "health", "promote", "audit")
@dataclass
class Rollout:
    completed: list = field(default_factory=list)
    stopped: bool = False
    def advance(self, stage, passed=True):
        if self.stopped:
            raise RuntimeError("rollout stopped")
        expected = ORDER[len(self.completed)] if len(self.completed) < len(ORDER) else None
        if stage != expected:
            self.stopped = True
            raise ValueError("stage order invalid")
        if not passed:
            self.stopped = True
            raise PermissionError("failed gate: " + stage)
        self.completed.append(stage)
        return tuple(self.completed)
