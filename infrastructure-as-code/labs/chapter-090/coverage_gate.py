"""Offline synthetic layer coverage; not actual test-run verification."""
REQUIRED={'static','unit','policy','terratest','molecule','cloud','kubernetes','gitops','drift','db_restore','audit'}
def assess(report):
    if not isinstance(report,dict):return ['report invalid']
    errors=[]
    layers=report.get('layers')
    if not isinstance(layers,list) or set(layers)!=REQUIRED or len(layers)!=len(REQUIRED):errors.append('layers incomplete')
    ids=report.get('test_ids')
    if not isinstance(ids,list) or len(ids)<10 or len(ids)!=len(set(map(str,ids))) or any(not isinstance(x,str) or not x.strip() for x in ids):errors.append('test IDs invalid')
    if type(report.get('skipped_critical')) is not int or report['skipped_critical']!=0:errors.append('critical skipped')
    if report.get('negative_policy_tests') is not True:errors.append('negative policy tests absent')
    if report.get('db_restore_claimed') is not True:errors.append('DB restore claim absent')
    return errors
