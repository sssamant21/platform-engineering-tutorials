"""Conservative synthetic drift decision; no auto-remediation."""
def decide(finding):
    if not isinstance(finding,dict):return 'quarantine'
    env=finding.get('environment');impact=finding.get('impact')
    if env not in ('dev','staging','production') or impact not in ('low','medium','high','critical'):return 'quarantine'
    if type(finding.get('destructive')) is not bool or type(finding.get('database')) is not bool:return 'quarantine'
    if finding['destructive'] or impact in ('high','critical') or (env=='production' and finding['database']):return 'quarantine'
    if impact=='medium' or env=='production':return 'review'
    return 'notify'
