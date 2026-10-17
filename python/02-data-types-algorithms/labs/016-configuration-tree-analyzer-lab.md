# Chapter 016 — Hands-on Lab: SRE Configuration Tree Analyzer

## Objective
Analyze a synthetic nested configuration tree stored in JSON. Validate the schema, traverse iteratively without recursion, compute node and leaf counts, find maximum depth, and produce deterministic JSON. No live infrastructure access.

## Step 1 — Create `tree.json`
```json
{
  "name": "platform",
  "children": [
    {"name": "api", "children": []},
    {"name": "data", "children": [
      {"name": "postgres", "children": []},
      {"name": "redis", "children": []}
    ]}
  ]
}
```

## Step 2 — Create `tree_analyzer.py`
```python
"""Read-only iterative configuration-tree analyzer."""
import argparse
import json
from pathlib import Path


def positive_int(raw: str) -> int:
    try:
        number = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def nonnegative_int(raw: str) -> int:
    try:
        number = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return number


def analyze(root: object, max_nodes: int = 1000, max_depth: int = 20) -> dict:
    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth must be nonnegative")
    pending = [(root, 0, "")]
    paths = []
    leaves = 0
    deepest = 0
    while pending:
        node, depth, parent_path = pending.pop()
        if depth > max_depth:
            raise ValueError("maximum depth exceeded")
        if not isinstance(node, dict) or set(node) != {"name", "children"}:
            raise ValueError("each node requires exactly name and children")
        name = node["name"]
        children = node["children"]
        if not isinstance(name, str) or not name.strip() or "/" in name:
            raise ValueError("node name must be nonempty and contain no slash")
        if not isinstance(children, list):
            raise ValueError("children must be an array")
        path = f"{parent_path}/{name}" if parent_path else name
        paths.append(path)
        if len(paths) > max_nodes:
            raise ValueError("maximum node count exceeded")
        deepest = max(deepest, depth)
        if not children:
            leaves += 1
        for child in reversed(children):
            pending.append((child, depth + 1, path))
    return {
        "node_count": len(paths),
        "leaf_count": leaves,
        "max_depth": deepest,
        "paths_preorder": paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only configuration-tree report")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--max-nodes", type=positive_int, default=1000)
    parser.add_argument("--max-depth", type=nonnegative_int, default=20)
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as source:
            root = json.load(source)
        report = analyze(root, args.max_nodes, args.max_depth)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Step 3 — Create `test_tree_analyzer.py`
```python
import argparse
import unittest
from tree_analyzer import analyze, positive_int, nonnegative_int

def node(name="root", children=None):
    return {"name": name, "children": [] if children is None else children}

class TreeAnalyzerTests(unittest.TestCase):
    def test_single_node(self):
        self.assertEqual(analyze(node())["node_count"], 1)
    def test_leaf(self):
        self.assertEqual(analyze(node())["leaf_count"], 1)
    def test_depth(self):
        self.assertEqual(analyze(node(children=[node("child")]))["max_depth"], 1)
    def test_preorder(self):
        tree = node(children=[node("a"), node("b")])
        self.assertEqual(analyze(tree)["paths_preorder"], ["root", "root/a", "root/b"])
    def test_nested_paths(self):
        tree = node(children=[node("a", [node("x")])])
        self.assertEqual(analyze(tree)["paths_preorder"][-1], "root/a/x")
    def test_duplicate_labels_different_paths(self):
        tree = node(children=[node("a", [node("x")]), node("b", [node("x")])])
        self.assertEqual(analyze(tree)["node_count"], 5)
    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            analyze([])
    def test_missing_children(self):
        with self.assertRaises(ValueError):
            analyze({"name": "root"})
    def test_invalid_children(self):
        with self.assertRaises(ValueError):
            analyze({"name": "root", "children": None})
    def test_empty_name(self):
        with self.assertRaises(ValueError):
            analyze(node(""))
    def test_slash_name(self):
        with self.assertRaises(ValueError):
            analyze(node("a/b"))
    def test_max_nodes(self):
        with self.assertRaises(ValueError):
            analyze(node(children=[node("a")]), max_nodes=1)
    def test_max_depth(self):
        with self.assertRaises(ValueError):
            analyze(node(children=[node("a")]), max_depth=0)
    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            analyze(node(), max_nodes=True)
    def test_positive_int_parser(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")
    def test_nonnegative_int_parser(self):
        self.assertEqual(nonnegative_int("0"), 0)

if __name__ == "__main__":
    unittest.main()
```

## Step 4 — Run
```bash
python tree_analyzer.py --input tree.json
python tree_analyzer.py --input tree.json --max-depth 1
python -m unittest -v test_tree_analyzer.py
python -m py_compile tree_analyzer.py
```
Expected for the default fixture: 5 nodes, 3 leaves, maximum depth 2, and paths `platform`, `platform/api`, `platform/data`, `platform/data/postgres`, `platform/data/redis`. The second command should fail safely because depth 2 exceeds the configured budget. Sixteen unit tests are provided.

## Step 5 — Failure injection
1. Remove a `children` field: validation error.
2. Set `children` to `null`: validation error.
3. Set `--max-nodes 2`: validation error.
4. Set `--max-depth 1`: validation error.
5. Use malformed JSON: input error.

## Operational considerations
This is a tree, not a general graph. It assumes acyclic JSON object nesting and does not detect service dependency cycles. Large JSON files are fully parsed before traversal; production tools should enforce input byte limits and use a bounded parser where appropriate. No production changes or remote calls are performed.

## Acceptance checklist
- [ ] Correct DFS pre-order paths
- [ ] Correct node, leaf and depth counts
- [ ] Validation rejects malformed nodes
- [ ] Depth and node budgets enforced
- [ ] Sixteen tests pass
- [ ] Read-only behavior

## Cleanup
Remove only the files created for this lab.
