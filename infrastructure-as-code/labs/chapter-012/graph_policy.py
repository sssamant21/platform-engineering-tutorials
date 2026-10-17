"""Educational dependency-inventory validator; not a Terraform DOT parser."""
import json
import sys
from pathlib import Path

def validate(data):
    if not isinstance(data, dict):
        return ["inventory must be object"]
    errors = []
    if data.get("environment") not in ("dev", "staging", "prod"):
        errors.append("invalid environment")
    if data.get("environment") == "prod" and data.get("auto_apply") is not False:
        errors.append("production auto_apply prohibited")
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return errors + ["nodes must be nonempty list"]
    graph = {}
    for i, node in enumerate(nodes):
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"]:
            errors.append(f"nodes[{i}]: invalid id")
            continue
        name = node["id"]
        if name in graph:
            errors.append(f"duplicate id: {name}")
        deps = node.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            errors.append(f"{name}: invalid depends_on")
            deps = []
        graph[name] = deps
        if data.get("environment") == "prod" and node.get("kind") == "database" and node.get("action") in ("delete", "replace") and node.get("dbre_approved") is not True:
            errors.append(f"{name}: destructive database change requires DBRE approval")
    for name, deps in graph.items():
        for dep in deps:
            if dep not in graph:
                errors.append(f"{name}: missing dependency {dep}")
    visiting, visited = set(), set()
    def visit(name):
        if name in visiting:
            errors.append(f"cycle detected at {name}")
            return
        if name in visited:
            return
        visiting.add(name)
        for dep in graph.get(name, []):
            if dep in graph:
                visit(dep)
        visiting.remove(name)
        visited.add(name)
    for name in graph:
        visit(name)
    return errors

def main(argv):
    if len(argv) != 2:
        print("Usage: python3 graph_policy.py graph.json")
        return 1
    try:
        errors = validate(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        print("DENY:", exc)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: dependency inventory policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
