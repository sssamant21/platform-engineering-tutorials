import json
import sys
from pathlib import Path

def validate(manifest, plan, policy):
    errors = []
    if not isinstance(manifest, dict) or not isinstance(plan, dict) or not isinstance(policy, dict):
        return ['invalid input']
    if manifest.get('environment') not in policy.get('allowed_environments', []):
        errors.append('environment')
    for section in ('compatibility', 'state', 'delivery', 'operations'):
        if not isinstance(manifest.get(section), dict):
            errors.append(section)
    for item in plan.get('resource_changes', []):
        if 'delete' in item.get('change', {}).get('actions', []):
            errors.append('destructive change')
    return errors

if __name__ == '__main__':
    m, p, policy = [json.loads(Path(x).read_text()) for x in sys.argv[1:4]]
    problems = validate(m, p, policy)
    print('PASS' if not problems else 'REJECT: ' + ', '.join(problems))
    raise SystemExit(bool(problems))
