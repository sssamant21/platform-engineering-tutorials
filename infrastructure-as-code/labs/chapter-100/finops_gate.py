from dataclasses import dataclass
@dataclass(frozen=True)
class Candidate:
    savings_cents:int
    p99_cpu:float
    failover_headroom:float
    slo_burn:float
    backup_ok:bool
    restore_ok:bool
    rollback_ok:bool
    finance_ok:bool
    sre_ok:bool
    dbre_ok:bool

def reconcile(rows, invoice_cents):
    ids=[r["id"] for r in rows]
    if len(ids)!=len(set(ids)) or any(r["cents"]<0 or not r["owner"] for r in rows):
        raise ValueError("invalid ledger")
    return sum(r["cents"] for r in rows)==invoice_cents

def gate(c):
    checks={"savings":c.savings_cents>0,"peak":c.p99_cpu<=70,
            "failover":c.failover_headroom>=30,"slo":c.slo_burn<=1,
            "backup":c.backup_ok,"restore":c.restore_ok,
            "rollback":c.rollback_ok,"finance":c.finance_ok,
            "sre":c.sre_ok,"dbre":c.dbre_ok}
    return {"decision":"STAGING_ONLY" if all(checks.values()) else "BLOCK",
            "failed":[k for k,v in checks.items() if not v]}
