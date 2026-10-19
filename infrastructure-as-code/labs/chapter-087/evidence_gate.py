"""Synthetic integration test report schema; not native evidence verification."""
REQUIRED={'terraform','terratest','molecule','kubernetes','gitops','database_restore'}
def assess(e):
    if not isinstance(e,dict):return ['report invalid']
    errors=[]
    layers=e.get('layers')
    if not isinstance(layers,list) or set(layers)!=REQUIRED or len(layers)!=len(REQUIRED):errors.append('missing layers')
    for k,minv in (('native_assertions',5),('negative_tests',10)):
        v=e.get(k)
        if type(v) is not int or v<minv:errors.append(k+' insufficient')
    if type(e.get('skipped_critical')) is not int or e['skipped_critical']!=0:errors.append('critical skipped')
    if e.get('cleanup_signed_off') is not True:errors.append('cleanup approval missing')
    return errors
