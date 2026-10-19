"""Offline state machine: no ansible/kubectl/Argo/Flux subprocesses."""
from dataclasses import dataclass,field
STAGES=('validate','inventory','dryrun','diff','policy','approve','backup','canary','health','promote','audit')
@dataclass
class Promotion:
    completed:list=field(default_factory=list)
    stopped:bool=False
    def advance(self,stage,passed=True):
        if self.stopped:raise RuntimeError('promotion halted')
        expected=STAGES[len(self.completed)] if len(self.completed)<len(STAGES) else None
        if stage!=expected:
            self.stopped=True;raise ValueError('out-of-order stage')
        if passed is not True:
            self.stopped=True;raise PermissionError('failed gate '+stage)
        self.completed.append(stage)
        return tuple(self.completed)
