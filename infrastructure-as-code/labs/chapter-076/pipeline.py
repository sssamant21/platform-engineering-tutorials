"""Pure offline CI/CD stage machine; never deploys infrastructure."""
from dataclasses import dataclass,field
from gate import STAGES
@dataclass
class Delivery:
    completed:list=field(default_factory=list)
    halted:bool=False
    def advance(self,stage,passed=True):
        if self.halted:raise RuntimeError('pipeline halted')
        expected=STAGES[len(self.completed)] if len(self.completed)<len(STAGES) else None
        if stage!=expected:
            self.halted=True
            raise ValueError('invalid stage ordering')
        if not passed:
            self.halted=True
            raise PermissionError('gate failed: '+stage)
        self.completed.append(stage)
        return tuple(self.completed)
