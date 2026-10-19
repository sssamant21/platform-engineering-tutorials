"""Offline secret rotation state machine; never touches real secrets."""
from dataclasses import dataclass,field
STAGES=('prepare','distribute','verify','revoke','audit')
@dataclass
class Rotation:
    completed:list=field(default_factory=list)
    halted:bool=False
    def advance(self,stage,healthy=True):
        if self.halted:raise RuntimeError('rotation halted')
        expected=STAGES[len(self.completed)] if len(self.completed)<len(STAGES) else None
        if stage!=expected:
            self.halted=True;raise ValueError('out of order')
        if healthy is not True:
            self.halted=True;raise PermissionError('rotation gate failed: '+stage)
        self.completed.append(stage)
        return tuple(self.completed)
