"""Static cardinality preflight, not live TSDB measurement."""
FORBIDDEN={'resource_id','trace_id','span_id','commit_sha','user_id','query','arn','request_id','pod_uid'}
ALLOWED={'environment','tool','stage','outcome','region','provider','risk','controller','engine','service'}
def assess(labels,max_series=10000):
    if not isinstance(labels,dict) or not labels:return ['labels invalid'],None
    if type(max_series) is not int or max_series<=0:return ['series budget invalid'],None
    errors=[];count=1
    for name,value in labels.items():
        if name in FORBIDDEN or name not in ALLOWED:errors.append('forbidden or unknown label '+str(name))
        if type(value) is not int or not 1<=value<=1000:errors.append('invalid cardinality '+str(name))
        else:count*=value
    if count>max_series:errors.append('series budget exceeded')
    return errors,count
