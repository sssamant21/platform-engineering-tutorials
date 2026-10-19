"""Simplified offline IAM allow-list simulator, not AWS/Azure/GCP IAM semantics."""
def assess(policy):
    if not isinstance(policy,dict):return ['IAM policy invalid']
    errors=[]
    for k in ('environment','principal','resource'):
        if not isinstance(policy.get(k),str) or not policy[k].strip():errors.append('missing '+k)
    if policy.get('environment')!='lab':errors.append('non-lab target')
    if policy.get('principal')!='ci-lab':errors.append('unexpected principal')
    if policy.get('resource')!='arn:aws:s3:::iac-lab-state/*':errors.append('resource not scoped')
    actions=policy.get('actions')
    if not isinstance(actions,list) or not actions or any(a not in ('s3:GetObject','s3:PutObject') for a in actions) or len(actions)!=len(set(actions)) if isinstance(actions,list) else True:
        errors.append('actions not scoped')
    if policy.get('passrole') is not False:errors.append('PassRole prohibited')
    return errors
