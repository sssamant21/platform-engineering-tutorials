"""Simplified namespace RBAC allow-list simulator, not Kubernetes authorization API."""
ALLOWED={'get','list'}
def assess(binding):
    if not isinstance(binding,dict):return ['RBAC invalid']
    errors=[]
    if binding.get('namespace')!='demo-security':errors.append('namespace mismatch')
    if binding.get('service_account')!='app-reader':errors.append('service account mismatch')
    if binding.get('resource')!='configmaps':errors.append('resource mismatch')
    verbs=binding.get('verbs')
    if not isinstance(verbs,list) or not verbs or any(v not in ALLOWED for v in verbs) or len(verbs)!=len(set(verbs)) if isinstance(verbs,list) else True:errors.append('verbs overbroad')
    if binding.get('cluster_scope') is not False:errors.append('cluster scope prohibited')
    if binding.get('automount_token') is not False:errors.append('token automount prohibited')
    return errors
