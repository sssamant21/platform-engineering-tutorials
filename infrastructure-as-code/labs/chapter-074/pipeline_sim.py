"""Offline CI/CD state machine: no Pulumi or cloud calls."""
from dataclasses import dataclass, field

ORDER = ("validate", "preview", "approve", "canary", "health", "promote")

@dataclass
class Pipeline:
    stages: list = field(default_factory=list)
    stopped: bool = False

    def advance(self, stage, allowed=True):
        if self.stopped:
            raise RuntimeError("pipeline already stopped")
        expected = ORDER[len(self.stages)] if len(self.stages) < len(ORDER) else None
        if stage != expected:
            self.stopped = True
            raise ValueError("out-of-order stage")
        if not allowed:
            self.stopped = True
            raise PermissionError("gate rejected " + stage)
        self.stages.append(stage)
        return tuple(self.stages)
