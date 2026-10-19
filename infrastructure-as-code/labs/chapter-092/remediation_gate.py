"""Conservative simulated remediation eligibility. No apply or destroy."""
def decide(f):
    if not isinstance(f,dict):return 'quarantine'
    if f.get('environment') not in ('dev','staging','production') or f.get('kind') not in ('configuration','identity','policy','state','gitops','database','security','cost','evidence','unknown') or f.get('severity') not in ('low','medium','high','critical'):return 'quarantine'
    for k in ('destructive','database','fresh','inventory_complete','approved','allowlisted'):
        if type(f.get(k)) is not bool:return 'quarantine'
    if f['destructive'] or f['database'] or f['kind'] in ('identity','policy','state','database','security','evidence','unknown') or f['severity'] in ('high','critical') or not f['fresh'] or not f['inventory_complete']:return 'quarantine'
    if f['environment']=='production' or f['severity']=='medium' or not f['approved'] or not f['allowlisted']:return 'review'
    return 'proposal_only'
