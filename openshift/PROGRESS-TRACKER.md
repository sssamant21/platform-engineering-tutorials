# OpenShift Administration — Progress and Validation

**Status key:** Planned · Drafted (documentation exists) · Reviewed · Lab verified · Production-approved.

| Chapter | Documentation | Runtime validation | Independent review | Production-approved |
| --- | --- | --- | --- | --- |
| 001 — OCP architecture and health | Drafted | Not run | Pending | No |
| 002 — CLI, console and access | Drafted | Not run | Pending | No |
| 003 — Control plane and nodes | Drafted | Not run | Pending | No |
| 004 — Cluster Operators and CVO | Drafted | Not run | Pending | No |
| 005 — Machines and node operations | Drafted | Not run | Pending | No |
| 006 — Workload lifecycle | Drafted | Not run | Pending | No |
| 007 — Projects and quotas | Drafted | Not run | Pending | No |
| 008 — Storage | Drafted | Not run | Pending | No |
| 009 — Networking and ingress | Drafted | Not run | Pending | No |
| 010 — Security and RBAC | Drafted | Not run | Pending | No |
| 011 — OLM and MachineConfig | Drafted | Not run | Pending | No |
| 012 — Monitoring and logging | Drafted | Not run | Pending | No |
| 013 — Capacity and autoscaling | Drafted | Not run | Pending | No |
| 014 — Upgrade procedures | Drafted | Not run | Pending | No |
| 015 — Backup and recovery | Drafted | Not run | Pending | No |
| 016 — Incident response | Drafted | Not run | Pending | No |
| 017 — Stateful workload operations | Drafted | Not run | Pending | No |
| 018 — Governance and acceptance | Drafted | Not run | Pending | No |

## Evidence policy

For each executed lab, record OCP exact version, cluster type (sanitized), time, namespace, commands, expected versus actual results, and reviewer. Store secrets nowhere in this repo. Runtime checks on a real cluster have **not** been performed as part of this initial track setup.

## Chapter 002 documentation milestone

Chapter, read-only lab and CLI/RBAC triage runbook drafted and cross-linked. Commands reviewed against the official OCP 4.22 CLI and web-console documentation. **No cluster runtime test, independent approval or production certification performed.**

## Chapter 003 documentation milestone

Chapter 003, read-only node/control-plane inventory lab and node runtime/MachineConfigPool triage runbook drafted and cross-linked. Reviewed against the official Red Hat OCP 4.22 RHCOS architecture and node overview documentation. **No cluster runtime execution, independent approval or production certification performed.**

## Chapter 004 documentation milestone

Chapter 004, read-only ClusterVersion/ClusterOperator lab and degraded-Operator triage runbook drafted. Technical condition semantics checked against Red Hat OCP 4.22 update and validation documentation. **No live cluster test, independent review, or production certification performed.**

## Chapter 005 documentation milestone

Chapter 005, read-only Machine API/Node inventory lab and MachineSet/node triage runbook drafted and linked. Includes topology applicability, Machine/Node mapping, production drain decision gates, stateful Kafka/PostgreSQL/Redis safeguards, expected errors and evidence templates. **No live cluster test, independent review or production certification performed.**

## Chapter 006 documentation milestone

Chapter 006, disposable deployment lab, and workload triage runbook drafted. The lab is explicitly non-production, requires a preapproved image digest, RBAC, restricted-SCC compatibility, resource controls and targeted cleanup. **No live cluster runtime test, independent review or production approval performed.**

## Chapter 007 documentation milestone

Chapter 007, read-only project governance lab and quota/LimitRange admission triage runbook drafted and cross-linked. Includes admission-control examples, tenant-isolation boundaries, policy-change approval and rollback caveats. **No live OCP runtime execution, independent review or production certification performed.**

## Chapter 008 documentation milestone

Chapter 008, read-only PV/PVC/StorageClass/CSI audit lab and storage incident triage runbook drafted and linked. Includes binding-versus-mount distinction, WaitForFirstConsumer, topology, multi-attach risks, stateful database safeguards, and escalation evidence. **No live OCP runtime execution, independent review or production certification performed.**

## Chapter 009 documentation milestone

Chapter 009, a read-only Service/EndpointSlice/Route audit lab, and a network/DNS/ingress triage runbook were drafted and linked. Guidance was checked against Red Hat OCP 4.22 OVN-Kubernetes, Networking Operators and networking overview documentation. Distinguishes backend readiness, external/internal DNS, Route admission, Ingress Operator and OVN network layers. **No live OCP execution, independent review or production certification performed.**

## Chapter 010 documentation milestone

Chapter 010, read-only RBAC/SCC/ServiceAccount audit and security access triage runbook drafted and linked. Reviewed command patterns and SCC visibility caveat against Red Hat OCP 4.22 authentication and authorization/RBAC documentation. **No live OCP execution, independent security review or production certification performed.**

## Chapter 011 documentation milestone

Chapter 011, read-only OLM/MCP audit lab and Operator/MachineConfig triage runbook drafted. Differentiates OLM add-ons from platform ClusterOperators, documents InstallPlan manual approval, CSV conditions, MCP rollout safeguards and stateful-service risks. **No live execution, independent review or production approval performed.**

## Chapter 012 documentation milestone

Chapter 012, read-only observability evidence lab, and monitoring/alert/log triage runbook drafted and linked. Includes OpenShift platform monitoring versus optional user-workload monitoring, logging deployment caveats, least-privilege checks, event retention limitations, sanitized evidence, and approval/rollback gates. **No live OCP execution, independent technical review or production approval performed.**

## Chapter 013 documentation milestone

Chapter 013, read-only capacity/scheduling lab and autoscaling triage runbook drafted. Covers allocatable versus requested capacity, node pressure, topology-aware scheduling, autoscaler applicability and stateful-workload change gates. **No live OCP execution, independent review or production certification performed.**

## Chapter 014 documentation milestone

Chapter 014 upgrade planning and gates, read-only preflight lab, and CVO/MCP upgrade triage runbook drafted and linked. No upgrade commands executed. OCP 4.22 is the documentation baseline; version-specific support path must be rechecked before any real change. **Live cluster testing, independent review and production approval remain pending.**

## Chapter 015 documentation milestone

Chapter 015, read-only recovery readiness lab, and etcd backup/recovery triage runbook drafted. Distinguishes etcd control-plane state from PV and database data, backup artifacts, quorum-loss escalation, RPO/RTO evidence and approval gates. **No cluster runtime execution, backup inspection, restore rehearsal, independent review or production approval performed.**

## Chapter 016 documentation milestone

Chapter 016, read-only incident triage lab and production-safety incident runbook drafted. Covers API availability, Degraded Operators, NotReady nodes, route errors, evidence hygiene, least privilege, stateful workload escalation and approval gates. **No live cluster execution, independent review or production certification performed.**

## Chapter 017 documentation milestone

Chapter 017, read-only stateful HA audit lab and incident runbook drafted and cross-linked. Covers database-native quorum versus Kubernetes readiness, CSI/PVC topology, PDB voluntary eviction limits, PostgreSQL/Kafka/MongoDB/Redis owner boundaries, fencing and irreversible-change safeguards. **No live OCP execution, independent technical review, database-native validation or production approval performed.**

## Chapter 018 documentation milestone

Chapter 018 enterprise governance and production acceptance, read-only audit lab, and change-gates runbook drafted and linked. Ownership matrix, least-privilege audit, acceptance evidence, rollback feasibility and stateful-workload approvals included. **All 18 chapters are now drafted; none is lab-verified, independently reviewed or production-approved.** Next: comprehensive Markdown/link, command, version-specific and safety review followed by authorized isolated runtime validation.

## V01 documentation and safety validation

[Validation gate plan](validation/V01-documentation-security-and-runtime-evidence-gates.md) drafted. This establishes chapter inventory, relative-link, command semantics, secrets, change-risk classification and runtime evidence requirements, prioritizing upgrades, etcd recovery, stateful HA and RBAC/SCC. **The comprehensive checks have not yet been executed; no independent review, live cluster testing or production approval is implied.** Next: perform branch-wide link inventory and resolve verified findings.

## V01 incremental link review — 2026-11-17

**Verified fix:** Chapter 015's Kubernetes fundamentals cross-track link incorrectly used `../../../kubernetes/README.md` from `openshift/chapters/`, which resolves above the repository root. Corrected to `../../kubernetes/README.md`; the target `kubernetes/README.md` was independently fetched from the active branch. The Chapter 015 link target was verified by repository path inspection, not a full Markdown link crawler. No Kubernetes files were changed.

**Scope and limits:** One confirmed relative-link defect fixed; complete branch-wide relative-link and external URL audits are **still pending**. Chapter 015 backup/recovery text was inspected for safety; this is **not** an independent OCP 4.22 command certification or a runtime restore test. All 18 chapters remain drafted only; no lab-tested or production-approved status is conferred.

**Next:** Scan every `openshift/` Markdown file for relative links and fenced commands; record file counts, broken targets and corrected links. Prioritize Chapters 014/015/017 version-specific and safety review, then authorized isolated lab evidence.

## V01 incremental RBAC semantic review — 2026-11-17

**Verified correction:** Chapter 017's Bash and PowerShell preflight previously used `oc auth can-i get pods` immediately before `oc get pods,statefulsets,pdb` (collection queries). Changed both to `oc auth can-i list pods` and documented that StatefulSets, PodDisruptionBudgets, nodes and StorageClasses also require separate `list` permissions. This corrects a least-privilege diagnostic mismatch; `get` on a named object is not equivalent to `list` on a collection. Chapter 017's changed file was committed on the existing draft PR branch.

**Review scope:** Manually inspected Chapters 014, 015 and 017 for safety wording, cross-track references and diagnostic authorization semantics. This was targeted textual review, **not** a full command certification, complete link crawl, OCP cluster test or independent review. Chapter 017 remains Drafted; no runtime or production approval status changes.

**Next:** Review labs/runbooks for the same `get` versus `list` mismatch; continue complete relative-link inventory and version-specific Red Hat 4.22 validation. Record real isolated cluster evidence only after authorized execution.

## V01 stateful HA lab RBAC follow-up — 2026-11-17

Reviewed Lab 017 against the Chapter 017 collection-query permission correction. Added explicit `list` checks for StatefulSets, PVCs, PDBs and events in Bash and PowerShell, distinguished cluster-scoped node/StorageClass permissions, and documented the `get` check for describing a named PDB. A `no` response requires skipping that read rather than elevating privileges. This is a documentation-only semantic review; commands were not executed against a cluster. Runbook 017 was inspected and already uses `list pods` for its collection preflight, but broader per-resource permission auditing remains pending. Full repository-wide audit, independent review and production approval remain pending.

## V01 stateful HA runbook authorization review — 2026-11-18

Corrected the Chapter 017 runbook's read-only collection workflow: previously it checked only `list pods` before querying pods, StatefulSets, PVCs, PDBs and events. It now requires independent `list` authorization for each namespace-scoped resource, separately checks cluster-scoped nodes and StorageClasses, and uses individually gated queries with Bash and PowerShell namespace syntax. Named-object `get` is distinguished from collection `list`; `no` means skip the query without privilege escalation. This is a **documentation-only** semantic correction, not live OCP execution or an independent security review. Full link audit, OCP 4.22 command review, isolated runtime evidence and production approval remain pending.

## V01 incident runbook least-privilege review — 2026-11-18

Reviewed Runbook 016's collection queries. Replaced the generic `oc auth can-i` instruction with resource-specific `list` checks for ClusterVersion, ClusterOperators, nodes, MCPs, pods, events, Routes, Services and EndpointSlices; added Linux/PowerShell preflight, separate named-object `get` guidance, expected failures and explicit skip/escalate behavior. Removed the combined multi-resource query so each read can be individually authorized. **Documentation-only semantic review**; no OCP cluster access, runtime execution, independent certification or production approval. Full Markdown link and command audits remain pending.

## V01 upgrade runbook RBAC review — 2026-11-18

Reviewed the Chapter 014 upgrade/CVO/MCP triage runbook and corrected a least-privilege gap: previously, cluster-wide reads of ClusterVersion, ClusterOperators, MachineConfigPools, nodes and events were shown without resource-specific authorization checks. Added Bash and PowerShell preflights, named ClusterVersion `get` versus collection `list` distinctions, an optional cluster-wide events gate, expected errors, evidence sanitization and stop-on-denial behavior. Commit `082f5c9f1907dc3f8959f938cea86bf21991784f`. Documentation-only review; no `oc` commands were run against an OCP cluster. Full Markdown link audit, exact OCP 4.22 command certification, isolated lab execution, independent review and production approval remain pending. Next: inspect Chapter 014 lab and other runbooks for authorization consistency, then conduct repository-wide link validation.

## V01 Chapter 014 upgrade lab authorization consistency — 2026-11-18

Corrected Lab 014 to gate each ClusterVersion (named `get`), ClusterOperator (`list`), MachineConfigPool (`list`) and node (`list`) read with matching least-privilege authorization. Explicitly handles `no`/`Forbidden`, avoids privilege escalation, includes PowerShell applicability and warns against sharing unredacted ClusterVersion JSON. Documentation-only review and commit `ebe959ecae73d1eb5dad31ab696e9432b01e5e28`; **no live cluster execution**. All 18 chapters remain Drafted; full link crawl, OCP 4.22 version-specific command verification, isolated lab evidence, independent review and production approval remain pending.

## V01 incident lab authorization consistency — 2026-11-18

Reviewed Lab 016 against the already-corrected incident-response runbook. Corrected an unsafe mismatch where only pods, nodes and ClusterOperators had permission preflights, while ClusterVersion, MachineConfigPools and events were also queried. The lab now checks separate collection `list` permissions for all six resources, gates each query on its own `yes`, distinguishes named-object `get` from `list`, and supplies explicit Bash and PowerShell namespace syntax, failure interpretation, evidence hygiene and change-approval boundaries. Commit evidence is in the draft PR branch. **Documentation-only validation:** no OCP cluster commands were run; no independent technical review or production approval. Remaining: full repository-wide Markdown link audit, version-specific command verification, isolated runtime tests and independent review.

## V01 Chapter 015 recovery lab authorization review — 2026-11-18

Corrected Lab 015's RBAC semantics: the previous `get clusterversion` preflight did not match its collection read, and Infrastructure/cluster was queried without a permission check. The lab now uses named-resource `get` for ClusterVersion/version and Infrastructure/cluster, `list` for ClusterOperators and nodes, individually gated reads, and explicit Bash/PowerShell workflows. Unauthorized/indeterminate checks skip reads without privilege escalation. Commit `80b5e7b29b393d02b0311cab9ba061e70a0f1a73`. **Documentation-only review:** no cluster execution, snapshot access, recovery test, independent review, or production approval. Next: inspect Chapter 015 runbook and remaining labs; complete the repository-wide link audit and OCP 4.22 command verification.

## V01 Chapter 015 recovery runbook RBAC review — 2026-11-18

Reviewed the etcd backup/recovery readiness triage runbook. Replaced unguarded collection reads with explicit, resource-specific authorization preflight: named `clusterversion/version` requires `get`, ClusterOperators and nodes require `list`. Added Bash and PowerShell examples, manual gating, expected `yes`/`no` and `Forbidden` handling, skip-without-elevation policy, and sensitive evidence handling. Commit `80a25e3f6b5b4c84df62298f21858af8c5c5a5d1`. **Documentation-level semantic review only**; no OpenShift API access, cluster execution, snapshot inspection, backup/restore test, independent technical review or production approval. Next: repository-wide Markdown link audit and version-specific OCP 4.22 command review, then isolated authorized lab validation.

## V01 validation-plan RBAC preflight correction — 2026-11-18

Corrected the V01 validation gate plan's Bash and PowerShell examples from `oc auth can-i get clusteroperators` to `oc auth can-i list clusteroperators`, matching the intended collection inventory (`oc get clusteroperators`). Named-object `get` requires a separate check. This is a documentation-level semantic correction only, not a completed repository-wide link audit, OCP 4.22 certification, runtime lab execution, independent review or production approval. Next: inventory and check all relative Markdown links across `openshift/` and record reproducible evidence.

## V01 reproducible local-link audit tooling — 2026-11-18

Added `validation/check_relative_links.py` (commit `32e30e74687c8bd0c959c744e016867a9e4e03f4`) to check relative Markdown link target existence under `openshift/` using Python standard library only. Run from repository root with `python openshift/validation/check_relative_links.py` (Windows: `py -3 openshift/validation/check_relative_links.py`). The script scans `.md` files, skips fenced code, excludes external URLs and fragments, reports missing paths and exits nonzero on failure. It is read-only and does not contact a cluster or network. **Tool authored and committed; full checkout execution and verified branch-wide findings remain pending** because no repository checkout was available in this run. Inline HTML links, reference-style Markdown links, anchors and external URL status are outside this initial checker scope. A targeted inspection of README and Chapters 014/015/017 link references was performed, not a full audit. Next: run the checker on a fresh checkout, fix actual broken links, extend coverage to reference links and verify Red Hat 4.22-sensitive commands; preserve independent review and lab-test gates.

## V01 reference-style link checker extension — 2026-11-18

Extended `validation/check_relative_links.py` to resolve explicitly defined reference-style Markdown links (`[text][id]` with preceding `[id]: path` definitions), in addition to inline links. This is an incremental static-analysis enhancement, **not** a complete Markdown parser: forward-declared references, collapsed/shortcut references, HTML links, anchors and external URL status are not yet covered. The full repository audit could not be executed in this environment because the GitHub checkout was unavailable (network DNS resolution failure); no pass/fail result is asserted. The changed file was committed on the existing draft PR branch. Next: obtain a complete checkout, run the checker, add regression fixtures, address actual broken targets and expand reference handling. No OCP runtime tests or production changes were performed.

## V01 reference-link parser repair and regression fixtures — 2026-11-18

Identified a static-analysis defect in `validation/check_relative_links.py`: the reference-definition and reference-use regular expressions contained doubled backslashes in raw strings, so actual reference links were not recognized. Corrected both expressions and added a two-pass definition collection that resolves forward-declared references while ignoring fenced definitions. Added `validation/test_check_relative_links.py` with offline cases for preceding/following definitions, missing targets and fenced definitions. Commits `6f8f5c645966a342ea860c3f90a9a207015f91fe` and `4706b99f822f9438266b360d4c7def734b1c5947`.

**Verification boundary:** GitHub accepted the commits; full checkout and Python test execution were blocked by DNS resolution to github.com in this runtime. The test file is authored but not executed, and no branch-wide link pass is claimed. The checker still does not validate HTML links, anchors, external URLs, or collapsed/shortcut references. Next: execute `python -m unittest discover -s openshift/validation -p 'test_*.py'` and `python openshift/validation/check_relative_links.py` in a complete checkout; record counts and fix confirmed defects. No OCP cluster execution, independent review or production approval.

## V01 collapsed-reference parser follow-up — 2026-11-18

Extended the read-only Markdown link validator to recognize collapsed reference links (`[label][]`) by resolving their label from the link text. Added offline regression cases for valid and missing collapsed-reference targets. This is a targeted source-level correction only: tests and the full branch-wide audit must be executed against a checkout before any pass can be claimed. External URLs, fragment anchors, shortcut references, and complete Markdown parsing remain outside current coverage. No OCP cluster execution, independent review, or production approval occurred.

## V01 reference-label normalization review — 2026-11-18

Corrected the offline Markdown link auditor to normalize case and runs of whitespace in reference labels, consistent with Markdown reference-label matching. Added one regression case covering mixed-case and multi-space labels; the suite now contains six test methods. Commits `78a29ff3f5aa09aa092d3b9155bf0cb6e99ef2ef` and `4b9d5c74806160cb0c837a3476dbe1b734d31bb8`. GitHub source retrieval verified both changes. Full checkout again failed because the runtime could not resolve github.com, so **neither the six-test suite nor the full branch link audit was executed**. No live OCP cluster testing, independent technical review or production approval. Next: execute `python -m unittest discover -s openshift/validation -p 'test_*.py'` and `python openshift/validation/check_relative_links.py` from a complete checkout; fix confirmed failures before version-specific command review.


## V01 duplicate-reference definition handling — 2026-11-18

Corrected the offline Markdown checker so the **first** definition of a normalized reference label wins; subsequent duplicate definitions no longer silently override it. Added a regression fixture with a valid first definition and broken duplicate second definition. Commits `66e323da7e1f15343e3b20483a3b856397b02f79` and `3affe28bc2b456d3869c4299c7840740bd1c2b3a`. The suite now has seven authored test cases. This is source-level validation only: neither tests nor a full repository audit have been executed in this run. No cluster testing, independent approval, or production certification.

Next: execute the seven regression tests and branch-wide link audit in a complete checkout; resolve actual failures and verify version-sensitive OCP 4.22 guidance.

## V01 inline-code false-positive correction — 2026-11-18

The local-link checker now ignores Markdown links inside single-backtick inline code spans while retaining real inline and reference links on the same line. Added one offline regression case (eight authored tests total). **Not yet executed:** the regression suite and complete branch-wide audit, because a repository checkout was unavailable due to DNS resolution. The change is a limited static-analysis improvement, not a complete Markdown parser: multi-backtick spans, HTML, anchors and external URL verification remain out of scope. No cluster commands or production operations were executed. Next: execute tests on a full checkout, fix confirmed link failures and continue OCP 4.22 review.

## V01 multi-backtick code-span link audit correction — 2026-11-18

Updated the read-only Markdown link checker to exclude matched single- and multi-backtick inline code spans while preserving navigable links elsewhere on the line. Unmatched delimiters remain visible for audit rather than silently suppressing links. Added two regression cases (ten authored tests total), covering multi-backtick spans and unmatched delimiters. Commits `5a588d395320e3f878a334119bbb9f3c9087422d` and `ddfae34dc6124e13284f1c3f0f0920078891556c`.

**Validation boundary:** GitHub accepted the changes; no full checkout-based Python test execution or branch-wide Markdown audit is claimed. This is a targeted source-level correction, not a complete CommonMark parser. HTML links, fragment anchors and external URL checks remain pending. No OpenShift cluster operations, independent review or production approval were performed.

**Next:** Run `python -m unittest discover -s openshift/validation -p 'test_*.py'` and `python openshift/validation/check_relative_links.py` from a complete checkout, record actual results, correct confirmed failures and review OCP 4.22-sensitive commands.

## V01 inline-code boundary regression — 2026-11-18

Static review found that deleting a matched backtick span without a separator could join adjacent text into a synthetic Markdown link. The checker now inserts a space where the span was removed; an eleventh offline regression case covers the boundary. Commits: `64ca518fe0e1159b1936536a6883cbf37a88602a`, `db058e4225941335e7f534a454ad1473272affac`. GitHub source updates are committed; Python tests and the complete link audit remain **unexecuted** because a complete checkout is unavailable (GitHub DNS resolution failed). No cluster access, production change, independent review or certification. Next: run the eleven regression cases and branch-wide audit from a complete checkout, record results and address real failures.


## V02 offline link-audit execution protocol — 2026-11-18

Added [V02 reproducible execution and evidence protocol](validation/V02-offline-link-audit-execution.md) with Linux/PowerShell commands, expected exit statuses, commit-SHA evidence requirements, limitations and escalation when checkout fails. A full GitHub checkout was attempted in this run but failed with `Could not resolve host: github.com`; **the 11 authored tests and full link audit have not been executed**. This is a documented QA procedure, not a passing result. Next: execute tests and the full checkout audit when network access is available; fix confirmed failures, then independently review OCP 4.22 commands and production safety.

## V01 Chapter 010 RBAC read authorization review — 2026-11-18

Corrected Chapter 010 namespace read preflights to distinguish `list` for RoleBindings, ServiceAccounts and pods from named Deployment `get`; added separate cluster-scope checks for ClusterRoleBindings and SCCs. Each read must be skipped on `no` or `Forbidden`; `who-can` may require additional authorization. Commits `afda288513e5dbf350abbae36c98c49778822e62` and `3757b947470fe0084c6d6dcc730e0aee7fde3ea2`. **Documentation-only review:** no OCP runtime test, full link audit, independent security approval or production certification. Next: execute offline regression tests and branch-wide link audit, then validate command semantics against OCP 4.22 documentation.

## V01 Chapter 010 security lab RBAC consistency — 2026-11-18

Corrected Lab 010's previously unguarded ServiceAccount and pod collection reads. The Linux/macOS and PowerShell examples now check `list` for RoleBindings, ServiceAccounts and pods, and `get` for the named Deployment (`--resource-name`). Each read is conditional on its own authorization result; denied or inconclusive checks are skipped without privilege escalation. Commit `79b0706dd437b73c1f6518bdc5077ae64477b9a0`. **Documentation-level semantic correction only:** no cluster commands executed; offline regression suite, full link audit, OCP 4.22 command verification, independent review and production approval remain pending.


## V01 Markdown fence indentation correction — 2026-11-18

Source inspection found the offline link checker treated four-space-indented backtick runs as fenced-code delimiters because its regex allowed arbitrary leading whitespace. Markdown fences permit at most three leading spaces; a four-space-indented line is indented code and must not toggle fence state. Restricted the detector to zero through three spaces and added two offline regression cases for four-space indentation and valid three-space fences. Commits `4bc6ee84760d4f3f9c8df4cc3366efa6a1b22e23` and `dbad7aadc38eb71fc2e4965706a370872632c41c`. **Source-level correction only:** the full regression suite and branch-wide link audit remain unexecuted, and no live cluster testing or production approval is claimed. Next: execute the tests and full audit on a complete checkout, then continue OCP 4.22 command/security review.

## V01 indented-code audit correction — 2026-11-18

Static review found that four-space and tab-indented code examples were still scanned for navigable links and reference definitions, potentially producing false missing-link findings or treating example definitions as real links. The read-only checker now skips these lines in both passes; two regression cases were added (13 authored tests in the currently retrieved test file). Commits `0675fd4124ba20b5100ec8201b98b768628e51e2` and `ff280ff946b3656586b5b3e146a93be6bca05c46`. **Not runtime-validated:** checkout again failed with `Could not resolve host: github.com`; the regression suite and full branch audit remain unexecuted. This limited checker does not implement complete Markdown block nesting or validate external URLs/fragments. No cluster operations or production approvals. Next: execute the suite and full audit on a complete checkout, fix confirmed failures, then continue OCP 4.22 security review.

## V01 fenced-code closing marker correction — 2026-11-18

Static review identified a false-positive risk: a line such as \`\`\`python inside an already-open fenced block is not a valid closing fence, but the audit previously closed the block and scanned subsequent code examples as links. The checker now closes a fence only when no non-whitespace text follows the delimiter; added one offline regression fixture (14 authored tests). Commits `67076ad88a71f34a4ce8e5096fb5247e518b550b` and `9c7692830c17f1ac60efb83124f0029f996a24d1`. **Tests and complete branch audit have not been executed:** this environment cannot resolve github.com for checkout. Source changes are not proof of passing validation. No cluster commands, production changes, independent review or certification. Next: run all 14 tests and full link audit from a complete checkout, then continue OCP 4.22 command review.


## V01 Chapter 010 named-resource authorization consistency — 2026-11-19

Reviewed Chapter 010 against its read-only Lab 010. The chapter's `oc auth can-i get deployments` preflight did not specify the Deployment being queried, whereas the lab correctly used `--resource-name`. Scoped the chapter's `get` authorization check to the named Deployment and clarified that this check is not a collection `list` grant. Commit `8021e7c9e604bfacad17e47b4428c158a3390aa9`. **Documentation-level semantic consistency review only**; no OpenShift cluster access or command execution, independent review or production approval. All 18 chapters remain drafted. Next: execute the offline Markdown regression suite and branch-wide link audit, then verify sensitive OCP 4.22 commands against official documentation and conduct authorized isolated lab tests.

## V01 Chapter 010 security runbook RBAC alignment — 2026-11-18

Corrected the RBAC/SCC/ServiceAccount incident runbook's earlier mismatch: it checked `get pods` but then ran unguarded collection reads of RoleBindings, ServiceAccounts and events, plus a named pod description. Added per-resource `list` preflights, named-pod `get` with `--resource-name`, explicit Bash and PowerShell workflows, cluster-scoped security-admin gates, skip-on-denial and evidence sanitization. Clarified that `use` SCC authorization is not equivalent to workload SCC admission. Commit `6618cbc23fa2b83b2a6e0ddb08dde1a8b2a86984`. **Documentation-only review:** no cluster access, executed `oc` validation, independent security approval or production certification. The 14 authored link regression tests and branch-wide link audit remain unexecuted; exact OCP 4.22 runtime behavior remains to be verified on an authorized isolated cluster.

## V01 invalid backtick-fence opening correction — 2026-11-18

Static review identified that the Markdown checker accepted an opening backtick fence whose info string itself contains a backtick (invalid under CommonMark), potentially hiding a real broken link. Both reference-definition and link-scanning passes now reject that opening marker; one regression test was authored. Commits `72036f70e347128deb2c56beac225087443fdf81` and `4edf5f0d7dd7e5ee99137856b2ba33e0733111dd`. There are now **17 authored unittest cases** across `test_check_relative_links.py` (15) and `test_fence_indentation.py` (2). **Not executed:** tests and full branch audit because direct GitHub checkout remains blocked by DNS resolution. GitHub source inspection and commits are not proof of test success. No cluster access, independent review or production approval. Next: execute the 17 tests and full audit from a complete checkout, then review version-sensitive OCP 4.22 operational guidance.


## V02 offline audit instructions reconciliation — 2026-11-19

Updated `validation/V02-offline-link-audit-execution.md` to reflect the 17 currently authored regression cases across two test modules (instead of the stale 11-case count), require checking discovery against the exact checkout SHA, and clarify that the audit scans only `openshift/` while resolving sibling Kubernetes links from a complete checkout without modifying Kubernetes content. Commit `9b8e0d0a36d4074f1443f0f6cadc04a41755089d`. **Documentation-only correction:** local Git checkout still fails with `Could not resolve host: github.com`; regression execution and full link audit remain blocked. No OCP cluster access, lab test, independent approval or production certification. Next: run the suite and full audit when checkout connectivity is restored, then address confirmed failures and continue version-specific technical review.


## V03 high-risk operational change review matrix — 2026-11-19

Added [V03 high-risk change review matrix](validation/V03-high-risk-change-review-matrix.md) covering upgrade, etcd recovery, MachineConfig, OLM, storage/stateful HA and RBAC/SCC change gates. It distinguishes permitted read-only evidence from approval-only actions, requires backup/fencing/version/topology checks and named independent signoffs, and explicitly rejects downgrade as an assumed upgrade rollback. Commit `4c10fa3cda19a25f7e5d12f2d37303b595593900`. **Drafted only:** no OCP cluster access, no command execution, no official release-specific command certification, no independent review or production approval. Next: run the 17 authored offline tests and link audit from a complete checkout; independently review high-risk runbooks against Red Hat 4.22 documentation and collect isolated lab evidence.


## V04 upgrade and etcd recovery evidence worksheet — 2026-11-19

Added [V04 upgrade and etcd recovery evidence worksheet](validation/V04-upgrade-etcd-recovery-evidence-worksheet.md), with least-privilege read-only preflights, version/upgrade-path gates, restore-rehearsal evidence, stop conditions, approval requirements and a reusable acceptance record. Commit `533d2a1da25af68ed715dc3a1b7c776244829cfb`. **Draft only:** no cluster execution, no verified restore, no Red Hat 4.22 command certification, no independent approval. A full Git checkout still fails with DNS resolution error; 17 offline tests and the full link audit remain pending. Next: run tests and audit from a complete checkout; verify OCP 4.22 release-specific recovery/upgrade guidance and collect isolated lab evidence.


## V04 named ClusterVersion read authorization correction — 2026-11-19

Corrected the V04 worksheet's `oc auth can-i get clusterversions.config.openshift.io` to check the specific `version` object using `--resource-name=version`, matching `oc get clusterversion version -o json`. Clarified that the inventory of `oc` commands is not a block to execute unconditionally: run each read only after its matching permission check succeeds. Commit `f64e82f30e9c7722cbb8b5250e8a41e92b450e68`. **Documentation-level RBAC review only**; no `oc` commands, Python tests, full link audit or isolated cluster restore were executed. Independent review and production approval remain pending. Next: execute 17 authored offline tests and branch-wide link audit from a complete checkout, then verify OCP 4.22 upgrade/recovery procedures against authoritative release-specific guidance.

## V04 executable authorization-gated diagnostic examples — 2026-11-19

Replaced the V04 worksheet's potentially misleading ungated inventory of `oc get` commands with separate Bash and Windows PowerShell examples. Each ClusterVersion (named `version`), ClusterOperator, node and MachineConfigPool read now runs only after an exact `yes` from its matching `oc auth can-i` check. Denied/inconclusive checks are skipped; failures require escalation. Removed default raw JSON collection to reduce inadvertent metadata exposure and documented context verification, output redaction and command failure boundaries. Commit `4b9f7edc69337e110912924e91d53fbdafcb603a`. **Documentation-only change:** no `oc` execution, runtime verification, independent review or production approval. The 17 authored offline tests and complete link audit remain pending. Next: execute the offline tests/audit and verify release-specific OCP 4.22 operational commands on an authorized isolated cluster.

## V04 authentication and cluster-context fail-closed review — 2026-11-19

Updated the V04 upgrade/etcd evidence worksheet to abort on failed `oc whoami`, require a verified active context against approved cluster inventory, and fail closed if `oc config current-context` fails in Bash or PowerShell. Added explicit warning that successful `can-i` authorization is not proof that the subsequent API read succeeds. Commits `2deb0eebeb14fe96861ac67b66a6c1ee05974f7f` and `9c51a8dfa052e209c06fbe51466c51ab03ea6224`. **Documentation-only safety correction**: no `oc` execution or independent review. Direct `git ls-remote` failed due to `Could not resolve host: github.com`; the 17 authored Python regression tests and complete link audit remain unexecuted. Next: run offline tests and branch-wide audit from a complete checkout, then conduct authorized OCP 4.22 version-specific command review and isolated lab validation.

## V04 enforce approved kube context — 2026-11-19

Corrected the Bash and PowerShell V04 diagnostic examples to require `EXPECTED_CONTEXT` from approved cluster inventory and fail closed on missing/mismatched active context. Previously the examples printed the context but relied on manual comparison without enforcing it. Commit `9f1ae412feac89eed707840dd488670a4316ab2d`. **Source review only:** no cluster execution, regression-suite execution, link audit or independent certification. Next: validate these scripts in an isolated authorized environment and execute the offline regression/link suite.
