"""Pure offline plan/apply state machine; no subprocess or cloud operations."""
from dataclasses import dataclass,field
STAGES=('validate','init','plan','policy','approval','backup','revalidate','apply','health','audit')
@dataclass
class Pipeline:
    completed:list=field(default_factory=list)
    halted:bool=False
    def advance(self,stage,ok=True):
        if self.halted:raise RuntimeError('halted')
        expected=STAGES[len(self.completed)] if len(self.completed)<len(STAGES) else None
        if stage!=expected:
            self.halted=True;raise ValueError('out of order')
        if ok is not True:
            self.halted=True;raise PermissionError('gate rejected '+stage)
        self.completed.append(stage)
        return tuple(self.completed)
