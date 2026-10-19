"""Request-based error budget and deduplicated change failure rate."""
from math import isfinite
def assess(changes,total_requests,failed_requests,objective=0.999):
    if not isinstance(changes,list) or not changes:return ['changes invalid'],None
    ids=set();failed=0
    for c in changes:
        if not isinstance(c,dict) or not isinstance(c.get('change_id'),str) or not c['change_id'] or c['change_id'] in ids or type(c.get('failed')) is not bool:return ['change invalid or duplicate'],None
        ids.add(c['change_id']);failed+=int(c['failed'])
    if type(total_requests) is not int or total_requests<=0 or type(failed_requests) is not int or not 0<=failed_requests<=total_requests:return ['requests invalid'],None
    if type(objective) not in (int,float) or not isfinite(objective) or not 0<objective<1:return ['objective invalid'],None
    allowed=total_requests*(1-objective)
    return [],{'change_failure_rate':failed/len(changes),'availability':1-failed_requests/total_requests,'error_budget_allowed':allowed,'error_budget_remaining':allowed-failed_requests,'error_budget_consumed':failed_requests/allowed}
