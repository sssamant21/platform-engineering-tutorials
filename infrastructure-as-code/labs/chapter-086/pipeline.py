"""Offline fail-closed test pipeline; no infrastructure apply."""
from dataclasses import dataclass,field
STAGES=('source','format','static','unit','policy','plan','integration','restore','canary','evidence','approval')
@dataclass
class Pipeline:
    completed:list=field(default_factory=list)
    halted:bool=False
    def advance(self,stage,passed=True):
        if self.halted:raise RuntimeError('pipeline halted')
        expected=STAGES[len(self.completed)] if len(self.completed)<len(STAGES) else None
        if stage!=expected:
            self.halted=True;raise ValueError('out of order')
        if passed is not True:
            self.halted=True;raise PermissionError('failed stage '+stage)
        self.completed.append(stage)
        return tuple(self.completed)
