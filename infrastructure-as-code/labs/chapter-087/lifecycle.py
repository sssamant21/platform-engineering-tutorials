"""Synthetic lease state machine; no cloud operations."""
from dataclasses import dataclass,field
STAGES=('requested','leased','provisioned','tested','cleanup_pending','destroyed','verified','closed')
@dataclass
class Lease:
    stages:list=field(default_factory=list)
    quarantined:bool=False
    def advance(self,stage,passed=True,owned_resources=None):
        if self.quarantined:raise RuntimeError('lease quarantined')
        expected=STAGES[len(self.stages)] if len(self.stages)<len(STAGES) else None
        if stage!=expected:
            self.quarantined=True;raise ValueError('out of order')
        if passed is not True:
            self.quarantined=True;raise PermissionError('failed stage '+stage)
        if stage in ('verified','closed') and (type(owned_resources) is not int or owned_resources!=0):
            self.quarantined=True;raise PermissionError('owned resources not independently verified zero')
        self.stages.append(stage)
        return tuple(self.stages)
