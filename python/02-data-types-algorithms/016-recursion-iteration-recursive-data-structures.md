# Chapter 016 — Recursion, Iteration and Recursive Data Structures

**Part 02 — Data Types and Algorithms | Python 3.10+ | 90–120 minutes**

## Learning outcomes
Explain recursion and base cases, compare recursive and iterative depth-first traversal, use explicit stacks and breadth-first queues, reason about complexity and recursion limits, validate nested JSON trees, and build a safe read-only SRE configuration-tree analyzer.

## 1. Recursion and base cases
A recursive function calls itself on a smaller subproblem and must reach a base case.

```python
def factorial(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a nonnegative integer")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

The time complexity is O(n), and the recursive call stack also consumes O(n) space. Python does not guarantee tail-call optimization; deeply nested input can raise `RecursionError`.

## 2. Iteration as an alternative
```python
def factorial_iterative(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a nonnegative integer")
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result
```
This version avoids recursive stack growth. Prefer iterative algorithms when input depth is untrusted or potentially large.

## 3. Trees as operational models
A service-dependency or configuration hierarchy can be modeled as nested nodes:
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
A tree has one root and each non-root node has one parent. Arbitrary service dependency graphs can have shared nodes and cycles; do not treat all dependency graphs as trees.

## 4. Recursive depth-first traversal
```python
def names_recursive(node: dict) -> list[str]:
    result = [node["name"]]
    for child in node["children"]:
        result.extend(names_recursive(child))
    return result
```
This concise form assumes trusted, acyclic, shallow input. For untrusted data, validate types and depth and avoid recursion on very deep trees.

## 5. Iterative depth-first traversal
```python
def names_iterative(root: dict) -> list[str]:
    stack = [root]
    result = []
    while stack:
        node = stack.pop()
        result.append(node["name"])
        stack.extend(reversed(node["children"]))
    return result
```
Reversing children preserves left-to-right pre-order traversal with a LIFO stack. Time complexity is O(V) for V tree nodes; the explicit stack uses O(height × branching factor) in the worst case, bounded by O(V).

## 6. Breadth-first traversal
```python
from collections import deque

def names_bfs(root: dict) -> list[str]:
    pending = deque([root])
    result = []
    while pending:
        node = pending.popleft()
        result.append(node["name"])
        pending.extend(node["children"])
    return result
```
BFS visits nodes level by level and may retain an entire wide level in memory.

## 7. Depth, node count and leaf count
Depth is measured from root depth 0. A leaf has no children. Define these terms explicitly in reports: maximum depth 2 means the deepest node is two edges below the root.

## 8. Operational safety
- Use a node-count and maximum-depth budget to reject unexpectedly large inputs.
- Validate every node's schema, including child types and required fields.
- Never run shell commands or perform remediation from tree labels.
- Keep output order deterministic.
- Do not assume that static dependency inventory reflects current production state.
- Never raise Python's global recursion limit just to accommodate untrusted data.

## 9. Failure scenarios
| Symptom | Cause | Mitigation |
|---|---|---|
| `RecursionError` | Excessive recursive depth | Iterative traversal and depth budget |
| `KeyError` | Missing name/children | Schema validation |
| `TypeError` | Child not a mapping | Validate node types |
| Excess memory | Very broad tree | Node limit and streaming strategy |
| Unexpected order | Stack child order reversed | Push children in reverse |
| Duplicate labels | Names not unique globally | Use path-based identities |
| Infinite traversal in graphs | Cyclic references | Track visited identities for graph inputs |

## 10. Hands-on lab
[Chapter 016 — SRE Configuration Tree Analyzer Lab](labs/016-configuration-tree-analyzer-lab.md) provides a complete Python CLI using iterative DFS, validated JSON tree input, maximum depth and node limits, deterministic summaries, automated tests and failure injection.

## 11. Exercises
1. Implement BFS and compare its order with DFS.
2. Explain why a repeated service name is not necessarily a duplicate identity.
3. Analyze time and space for a chain versus a wide tree.
4. Add a search function that returns all paths matching a label.
5. Explain why cycles require graph-aware traversal.

**Next:** Chapter 017 — Hashing, Lookup Tables and Deduplication.
