"""Pure offline promotion state machine; no subprocess or cloud calls."""
from dataclasses import dataclass,field
STAGES=('source','validate','preview','policy','approve','backup','revalidate','canary','health','promote','audit')
@dataclass
class Promotion:
    completed:list=field(default_factory=list)
    stopped:bool=False
    def advance(self,stage,passed=True):
        if self.stopped:raise RuntimeError('promotion stopped')
        expected=STAGES[len(self.completed)] if len(self.completed)<len(STAGES) else None
        if stage!=expected:
            self.stopped=True;raise ValueError('stage out of order')
        if passed is not True:
            self.stopped=True;raise PermissionError('gate rejected '+stage)
        self.completed.append(stage)
        return tuple(self.completed)
