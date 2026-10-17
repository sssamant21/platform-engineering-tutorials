"""Educational graph-manifest and plan-action policy, not a Terraform DOT parser."""
import json
import sys
from pathlib import Path

ALLOWED = {"no-op", "read", "create", "update", "delete"}

def validate(graph, plan, policy):
    if not all(isinstance(v, dict) for v in (graph, plan, policy)):
        return ["graph, plan and policy must be objects"]
    errors = []
    required = policy.get("required_nodes")
    required_edges = policy.get("required_edges")
    maximum = policy.get("max_nodes")
    if not isinstance(required, list) or not required or any(not isinstance(x, str) for x in required):
        errors.append("invalid required_nodes policy")
    if not isinstance(required_edges, list) or not all(isinstance(x, dict) for x in required_edges):
        errors.append("invalid required_edges policy")
    if type(maximum) is not int or maximum < 1:
        errors.append("invalid max_nodes policy")
    if policy.get("deny_deletes") is not True:
        errors.append("deny_deletes must be true")
    if errors:
        return errors
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not nodes or any(not isinstance(x, str) or not x for x in nodes):
        return ["nodes must be a nonempty list of names"]
    if len(nodes) != len(set(nodes)):
        errors.append("duplicate nodes")
    if len(nodes) > maximum:
        errors.append("node count exceeds cap")
    if not isinstance(edges, list):
        return errors + ["edges must be a list"]
    node_set = set(nodes)
    if not set(required).issubset(node_set):
        errors.append("required nodes missing")
    pairs = []
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict) or not isinstance(edge.get("before"), str) or not isinstance(edge.get("after"), str):
            errors.append(f"edge[{i}]: invalid structure")
            continue
        before, after = edge["before"], edge["after"]
        pairs.append((before, after))
        if before not in node_set or after not in node_set:
            errors.append(f"edge[{i}]: unknown node")
        if before == after:
            errors.append(f"edge[{i}]: self edge")
    if len(pairs) != len(set(pairs)):
        errors.append("duplicate edges")
    for item in required_edges:
        if (item.get("before"), item.get("after")) not in pairs:
            errors.append("required edge missing")
    adjacency = {n: [] for n in nodes}
    for before, after in pairs:
        if before in node_set and after in node_set:
            adjacency[before].append(after)
    colors = {}
    def visit(node):
        state = colors.get(node, 0)
        if state == 1:
            return True
        if state == 2:
            return False
        colors[node] = 1
        if any(visit(child) for child in adjacency[node]):
            return True
        colors[node] = 2
        return False
    if any(visit(node) for node in nodes if colors.get(node, 0) == 0):
        errors.append("dependency cycle detected")
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        errors.append("resource_changes must be a list")
    else:
        for i, item in enumerate(changes):
            change = item.get("change") if isinstance(item, dict) else None
            actions = change.get("actions") if isinstance(change, dict) else None
            if not isinstance(actions, list) or not actions or any(not isinstance(a, str) or a not in ALLOWED for a in actions):
                errors.append(f"resource_changes[{i}]: invalid actions")
            elif "delete" in actions:
                errors.append(f"resource_changes[{i}]: destructive action denied")
    return errors

def main(argv):
    if len(argv) != 4:
        print("Usage: python3 graph_policy.py <graph-json> <plan-json> <policy-json>")
        return 1
    try:
        graph, plan, policy = [json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[1:]]
        errors = validate(graph, plan, policy)
    except (OSError, ValueError) as exc:
        print("DENY:", type(exc).__name__)
        return 1
    for error in errors:
        print("DENY:", error)
    if errors:
        return 1
    print("PASS: educational graph and plan policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
