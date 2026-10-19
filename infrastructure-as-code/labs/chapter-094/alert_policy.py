"""Synthetic paired-window alert classifier; does not send notifications."""
WINDOWS=('5m','1h','30m','6h')
def classify(burns,counts,fresh=True,min_requests=100):
    if fresh is not True:return 'UNKNOWN'
    if not isinstance(burns,dict) or not isinstance(counts,dict) or set(burns)!=set(WINDOWS) or set(counts)!=set(WINDOWS):return 'UNKNOWN'
    if type(min_requests) is not int or min_requests<=0:return 'UNKNOWN'
    for name in WINDOWS:
        v=burns[name];n=counts[name]
        if type(v) not in (int,float) or not 0<=v<1e12 or type(n) is not int or n<min_requests:return 'UNKNOWN'
    if burns['5m']>=14.4 and burns['1h']>=14.4:return 'PAGE'
    if burns['30m']>=6 and burns['6h']>=6:return 'PAGE'
    if burns['6h']>=1:return 'TICKET'
    return 'OK'
