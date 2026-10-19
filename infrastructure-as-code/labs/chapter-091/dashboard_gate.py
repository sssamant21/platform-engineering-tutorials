"""Synthetic dashboard coverage; no Grafana API calls."""
REQUIRED={'pipeline','state','policy','drift','gitops','dbre','slo','audit'}
def assess(report):
    if not isinstance(report,dict):return ['dashboard invalid']
    errors=[]
    panels=report.get('panels')
    if not isinstance(panels,list) or set(panels)!=REQUIRED or len(panels)!=len(REQUIRED):errors.append('panels incomplete')
    for k in ('owner','runbook'):
        if not isinstance(report.get(k),str) or not report[k].strip():errors.append(k+' missing')
    age=report.get('freshness_minutes')
    if type(age) not in (int,float) or not 0<=age<=5:errors.append('dashboard stale')
    if report.get('unknown_when_missing') is not True:errors.append('missing telemetry incorrectly healthy')
    return errors
