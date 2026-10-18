import copy
import json
import unittest
from pathlib import Path
from migration_gate import validate
ROOT=Path(__file__).parent
SAFE=json.loads((ROOT/'fixtures/migration-safe.json').read_text())
UNSAFE=json.loads((ROOT/'fixtures/migration-unsafe.json').read_text())
PLAN=json.loads((ROOT/'fixtures/plan-safe.json').read_text())
DESTRUCTIVE=json.loads((ROOT/'fixtures/plan-destructive.json').read_text())
POLICY=json.loads((ROOT/'migration-policy.json').read_text())

class MigrationTests(unittest.TestCase):
    def test_safe(self): self.assertEqual(validate(SAFE,PLAN,POLICY),[])
    def test_invalid_environment(self):
        m=copy.deepcopy(SAFE);m['environment']='invalid';self.assertTrue(validate(m,PLAN,POLICY))
    def test_missing_sections(self):
        for section in ('compatibility','state','delivery','operations'):
            m=copy.deepcopy(SAFE);m.pop(section);self.assertTrue(validate(m,PLAN,POLICY))
    def test_destructive(self): self.assertTrue(validate(SAFE,DESTRUCTIVE,POLICY))
    def test_unsafe_fixture(self): self.assertTrue(validate(UNSAFE,DESTRUCTIVE,POLICY))
    def test_noop(self): self.assertEqual(validate(SAFE,PLAN,POLICY),[])

if __name__=='__main__': unittest.main()
