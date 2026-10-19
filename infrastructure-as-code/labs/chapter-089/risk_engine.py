"""Deterministic synthetic drift scoring; never authorize remediation."""
def assess(e):
    if not isinstance(e,dict):return ['finding invalid'],None
    errors=[]
    for k in ('environment','exposure','data_impact','destructive','approved'):
        if k not in e:errors.append(k+' missing')
    if errors:return errors,None
    if e['environment'] not in ('dev','staging','production'):errors.append('environment invalid')
    if e['exposure'] not in ('private','internal','public'):errors.append('exposure invalid')
    if e['data_impact'] not in ('none','limited','regulated'):errors.append('data impact invalid')
    if type(e['destructive']) is not bool:errors.append('destructive invalid')
    if type(e['approved']) is not bool:errors.append('approval invalid')
    if errors:return errors,None
    score={'dev':0,'staging':10,'production':25}[e['environment']]
    score+={'private':0,'internal':10,'public':30}[e['exposure']]
    score+={'none':0,'limited':10,'regulated':25}[e['data_impact']]
    if e['destructive']:score+=30
    if not e['approved']:score+=20
    return [],min(score,100)
