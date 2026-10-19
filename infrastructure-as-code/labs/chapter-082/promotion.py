"""Offline fail-closed promotion sequence. No cloud apply."""
from dataclasses import dataclass,field
STAGES=('source','preview','scan','policy','approval','backup','canary','health','promote','audit')
@dataclass
class Promotion:
    completed:list=field(default_factory=list)
    halted:bool=False
    def advance(self,stage,passed=True):
        if self.halted:raise RuntimeError('halted')
        expected=STAGES[len(self.completed)] if len(self.completed)<len(STAGES) else None
        if stage!=expected:
            self.halted=True;raise ValueError('out of order')
        if passed is not True:
            self.halted=True;raise PermissionError('failed gate '+stage)
        self.completed.append(stage)
        return tuple(self.completed)
