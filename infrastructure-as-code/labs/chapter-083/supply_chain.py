"""Metadata schema check; not cryptographic signature/provenance verification."""
import re
def assess(e):
    if not isinstance(e,dict):return ['attestation invalid']
    errors=[]
    for k in ('source_commit','builder_id','sbom_digest','artifact_digest','provenance_digest'):
        if not isinstance(e.get(k),str) or not e[k].strip():errors.append(k+' missing')
    for k in ('sbom_digest','artifact_digest','provenance_digest'):
        if not isinstance(e.get(k),str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',e[k]):errors.append(k+' malformed')
    if e.get('builder_id')!='offline-trusted-builder':errors.append('builder identity untrusted')
    if e.get('source_commit')!='0123456789abcdef':errors.append('source mismatch')
    return errors
