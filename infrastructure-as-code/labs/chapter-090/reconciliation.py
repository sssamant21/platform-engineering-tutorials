"""Offline approval state machine; no cloud operations."""
from dataclasses import dataclass,field
STAGES=('detected','classified','approved','reconciled','verified','closed')
@dataclass
class Case:
    stages:list=field(default_factory=list)
    quarantined:bool=False
    def advance(self,stage,passed=True,independent_approval=False,slo_healthy=False):
        if self.quarantined:raise RuntimeError('quarantined')
        expected=STAGES[len(self.stages)] if len(self.stages)<len(STAGES) else None
        if stage!=expected:
            self.quarantined=True;raise ValueError('out of order')
        if passed is not True:
            self.quarantined=True;raise PermissionError('failed stage')
        if stage in ('approved','reconciled') and independent_approval is not True:
            self.quarantined=True;raise PermissionError('approval absent')
        if stage in ('verified','closed') and slo_healthy is not True:
            self.quarantined=True;raise PermissionError('SLO unverified')
        self.stages.append(stage)
        return tuple(self.stages)
