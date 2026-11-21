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


## V04 pin approved API endpoint — 2026-11-19

Reviewed the V04 read-only preflight and found that checking only a kubeconfig context name cannot reliably identify the intended cluster because context names are local labels. Added required `EXPECTED_SERVER` matching against the active kubeconfig API endpoint in both Bash and PowerShell, with fail-closed behavior for missing, empty or mismatched endpoints. The check does not display the endpoint or replace TLS trust and independent inventory verification. Worksheet commit `551513df9424aae1a06e812199ca838f2fdda07e`. **Source-level review only:** no OpenShift cluster access, shell execution, 17-test regression suite, complete link audit, independent approval or production certification. Next: test both preflight scripts in an isolated environment and run the full offline validation suite.


## V05 isolated identity-guard regression matrix — 2026-11-19

Added [V05 mock-oc identity-guard regression matrix](validation/V05-isolated-identity-guard-regression-matrix.md) with 12 fail-closed, authorization-gating and read-failure scenarios for both Bash and PowerShell, including an explicit no-real-cluster boundary and sanitized evidence requirements. Document commit `16d80c8ef39c8b9e1344f7970e9d3b295b184e84`. **Drafted only:** the scenarios have not been executed, and neither 17 existing Python regression tests nor the full link audit has been completed. Next: implement/run mock tests from a complete checkout and independently review V04 against Red Hat 4.22 before authorized isolated OCP checks.

## V05 offline identity-guard test implementation (2026-11-19)

Added [`tests/test_v05_bash_identity_guard.py`](tests/test_v05_bash_identity_guard.py): nine isolated Bash scenarios using a mock `oc` executable, temporary HOME/KUBECONFIG/PATH and invocation-log assertions. These cover V05 I01–I07, plus all-authorized and all-denied reads. The tests extract the Bash example directly from the V04 worksheet; they do not invoke a real cluster. **Authored only: tests have not been executed or independently reviewed.** Run from the repository root with `python -m unittest discover -s openshift/tests -p 'test_v05_bash_identity_guard.py' -v` on Linux with Bash and Python 3. PowerShell coverage, mixed RBAC, failed reads and full regression execution remain pending. Do not interpret mock passes as production approval.

## V05 Bash negative-path expansion and V04 failed-read correction — 2026-11-19

Expanded `tests/test_v05_bash_identity_guard.py` from nine to thirteen authored tests, adding failed/ambiguous authorization, mixed resource permissions and failed authorized reads. Tightened the mock `oc config view` argument match. Corrected V04 Bash and PowerShell examples to terminate with a nonzero status on failed version queries or authorized diagnostic reads rather than continuing and potentially implying a healthy result. Commits `4d9692e2376200aadc41d2807049624cd931f7fe` and `73a429c663e0bfdb724e61912050904ae1f5ff77`. **Source-level correction only: the thirteen tests have not been executed in this run**, and PowerShell mock coverage, the original 17-test suite, full link audit, isolated OCP 4.22 checks and independent review remain pending. Next: execute the test harness in a complete checkout, inspect failures, and implement PowerShell scenarios without real cluster credentials.

## V05 PowerShell isolated mock coverage — 2026-11-19

Added [`tests/test_v05_powershell_identity_guard.py`](tests/test_v05_powershell_identity_guard.py) with eight authored PowerShell 7 scenarios. The harness extracts the actual V04 PowerShell block and shadows `oc` with a session-local function; it uses a nonexistent kubeconfig and a temporary invocation log. Cases include allowed/denied reads, missing or mismatched context/server, authentication failure, version failure and failed authorized reads. Commit `3419d854751b3233f1975dce6a756dd4134f7d1d`. **Authored, not executed or independently reviewed.** Run with `python -m unittest discover -s openshift/tests -p 'test_v05_powershell_identity_guard.py' -v` on a host with `pwsh` 7; absent PowerShell results in skips, not passes. Existing Bash tests, original 17-test suite, full link audit, isolated OCP checks and production approval remain pending. Next: execute both V05 suites and resolve actual failures; expand remaining scenario coverage.

## V05 Bash fail-closed exit-status assertion hardening — 2026-11-19

Reviewed the 13-case Bash mock-`oc` harness and found that seven identity rejection scenarios asserted only that no `oc get` occurred, without asserting a nonzero process exit. A script could silently return success while skipping all reads and still satisfy those tests. Updated `tests/test_v05_bash_identity_guard.py` to require a nonzero exit for missing expected context/server, failed authentication/context/server lookup, and mismatched context/server. Commit `80be65e5135d5c9d40e170ceada2a65f8b9c44a3`. **Source-level test correction only; no test execution or cluster access.** Next: execute the Bash and PowerShell suites plus the original 17 tests on a complete checkout, record actual PASS/FAIL/SKIP evidence, and complete the link audit. All 18 chapters remain drafted; independent review and production approval pending.

## V05 PowerShell authorization error handling — 2026-11-19

Corrected the V04 PowerShell diagnostic example so a nonzero `oc auth can-i` exit stops evidence collection rather than being silently reported as a denied/skipped read. An explicit `no` still skips without escalation. Added a ninth PowerShell mock test for authorization API errors, asserting nonzero exit, only one authorization attempt, and no resource reads. Commits `68294b9918455cd2b54423092fda9c7e17159c2a` and `102d8a5a10d455e946e7a635796e2343f14e5fb6`. **Source review only; tests not executed.** Bash currently skips failed authorization checks and requires separate follow-up for parity. Offline test execution, full link audit, isolated OCP 4.22 verification and independent review remain pending. All 18 chapters remain drafted, not production-approved.

## V05 Bash authorization-error fail-closed parity — 2026-11-19

Revised V04 Bash authorization checks for all four resources: a nonzero `oc auth can-i` result now stops immediately, explicit `no` skips, and any other response fails closed. Updated the existing V05 Bash mock assertions to require nonzero exit and no reads on failed or ambiguous authorization, with only one attempted check. **Source-level change only; no regression execution, cluster testing, link audit or independent approval claimed.** Next: execute offline Bash/PowerShell and original Python suites, record actual evidence, then independently review OCP 4.22 semantics.

## V05 PowerShell ambiguous authorization fail-closed correction — 2026-11-19

Source review found that the V04 PowerShell example treated any successful `oc auth can-i` response other than `yes` as a denial, including unexpected or malformed output. Updated all four resource gates to distinguish explicit `yes` (read), explicit `no` (skip), and any other response (throw/stop). Worksheet commit `28fedd0f624da705cac7e1d692ba407b6ef54f81`. **Source-only review:** no PowerShell regression execution, real OCP cluster access, independent review or production approval. Next: add a PowerShell mock test for ambiguous authorization, run all offline suites, and complete the link audit.

## V05 PowerShell ambiguous authorization regression — 2026-11-19

Added an isolated mock `oc auth can-i` response of `maybe` and a tenth PowerShell test requiring nonzero exit, exactly one authorization attempt and zero resource reads. Commit `ff94ef5dcb057896e257d3131601ca3a3959ad6d`. **Authored, not executed:** no PowerShell runtime test, cluster access, complete Markdown link audit, independent review or production approval. Next: run Bash (13), PowerShell (10) and existing offline validation tests from a complete checkout, capture actual PASS/FAIL/SKIP evidence, and correct confirmed failures. All 18 chapters remain drafted, not certified.

## V05 Bash mock regression review — 2026-11-19

Reviewed the actual V04 diagnostic order and corrected the failed-read test: when `oc get nodes` (third resource read) fails, the script must stop after **three** reads and must not query MachineConfigPools. The prior test incorrectly expected four reads, which would reward continuing after failure. Added `FAIL_VERSION` mock handling and a fourteenth Bash test requiring a failed `oc version` to stop before any authorization or resource read. Commit `2fff24ca32965f8a4139afbdebf89632c6a4d9c6`. **Source-level review only; no test execution claimed.** Pending: execute 14 Bash, 10 PowerShell and earlier regression tests in an isolated environment; record PASS/FAIL/SKIP, audit links, perform authorized OCP 4.22 checks and independent review. All 18 chapters remain drafted, not production-approved.

## V06 isolated regression execution protocol — 2026-11-19

Added [V06 execution and evidence protocol](validation/V06-offline-regression-execution-protocol.md) for separate Bash (14 authored), PowerShell (10 authored) and earlier offline unittest suites, including dependency checks, honest SKIP/BLOCKED classification, sanitized evidence, exit-code recording and production-readiness gates. Commit `e82e05abfcf9c116533850f0f4d86700b34f9fe5`. **Documentation authored only:** tests have not been executed; no cluster access, complete link audit or independent approval is claimed. Next: execute offline tests from a clean checkout, capture evidence, fix failures, then review version-specific OCP 4.22 guidance.

## V06 protocol correctness follow-up — 2026-11-19

Corrected the offline execution protocol to **run** `check_relative_links.py` rather than only display its `--help` interface. Clarified that unsetting `KUBECONFIG` alone is unsafe because a real client can fall back to the default home-directory kubeconfig; prescribed a nonexistent kubeconfig path in a disposable environment and harness-only execution. The link auditor's own source was inspected to confirm its documented read-only entry point. **Documentation correction only:** the regression suites and link auditor were not executed in this run. Runtime validation, independent review and production approval remain pending.

## V06 offline regression evidence template — 2026-11-19

Added [V06 blank evidence record](validation/V06-offline-regression-evidence-template.md) with exact commands, per-suite PASS/FAIL/ERROR/SKIP and exit-code fields, runner identity/isolation checks, failure triage, evidence sanitization and independent approval gates. Commit `62717d3d5dd9bf43b8734bc4f5cfc451985f903d`. **Template authored only; no suites or link audit executed.** Local Git checkout remains blocked by DNS; no real cluster access or production approval. Next: run the existing offline suites on a clean checkout and populate this record with genuine results.


## V06 PowerShell mock command allowlist — 2026-11-20

Reviewed the ten-case V05 PowerShell identity-guard harness. Replaced its narrow destructive-command denylist with a strict mock invocation allowlist covering only `whoami`, context/server inspection, `version`, `auth can-i` and `get`. This makes unexpected commands fail the harness assertion even if not included in the former denylist. Commit `ecba0caeddf98f1b85340200f687e44ea932b842`. **Source-level change only:** no PowerShell suite execution, OCP cluster test or independent approval. Next: run all offline suites and the link audit in a credential-isolated checkout, recording genuine results and investigating failures.

## V06 Bash diagnostic command allowlist — 2026-11-20

Strengthened `tests/test_v05_bash_identity_guard.py` to reject any command outside the exact expected identity, context, API endpoint, version, RBAC and four resource-read invocations. This closes a gap in the previous prefix-only assertion, which could accept unintended `oc get` resources or broadened authorization queries. Commit `24f56e231bc22195cf4d474b45a4f49c43d1b9bf` on the existing draft PR branch. **Source-level verification only:** checkout and offline test execution were blocked by DNS resolution to GitHub in this runtime. The 14 Bash, 10 PowerShell and earlier regression suites, complete link audit, isolated OCP 4.22 lab tests and independent approval remain pending. No production cluster accessed.


## V06 PowerShell exact-command allowlist review — 2026-11-20

Corrected a source-level regression harness gap: the PowerShell test previously accepted arbitrary `auth can-i *` and `get *` commands despite describing a strict allowlist. It now checks exact expected identity, context, endpoint, version, four authorization checks and four read-only resource queries, matching the Bash test's command scope. This detects unexpected resource reads and broadened RBAC checks in mock execution. **Source-level review and GitHub write verification only; offline tests have not been executed, and OCP runtime validation and independent approval remain pending.**

## V06 mock-only runner preflight — 2026-11-20

Added explicit Bash/Git Bash and PowerShell 7 disposable kubeconfig isolation preflights to the [V06 execution protocol](validation/V06-offline-regression-execution-protocol.md). Clarified that isolation alone does not prove safety: the harness must intercept every `oc` call, and uncertain interception is BLOCKED rather than executed. No real `oc` preflight is allowed. **Documentation reviewed and committed, not executed.** All offline test suites, link audit, isolated OCP 4.22 runtime validation and independent approval remain pending.


## V06 PowerShell preflight coverage increment — 2026-11-20

Added two **authored, not executed** PowerShell regression cases for a missing expected API server and a failed server lookup. Both require a nonzero exit and no authorization checks or resource reads. Tightened the mock server lookup to match the exact expected `oc config view --minify -o jsonpath={.clusters[0].cluster.server}` command instead of a wildcard. PowerShell V05 suite now has **12 authored tests**; Bash suite remains at **14 authored tests**. GitHub source/commit verification is not runtime execution. **Pending:** execute the suites offline with sanitized PASS/FAIL/SKIP evidence, link audit, isolated OCP 4.22 validation, and independent review. No production approval.

## V06 PowerShell fail-closed ordering regressions — 2026-11-20

Strengthened the version-failure regression to require exactly one version query and **zero subsequent RBAC checks or resource reads**. Added an explicit four-denial scenario asserting all four authorization checks occur without any resource reads, and a failed-context-lookup scenario asserting that server lookup, RBAC checks and resource reads never occur. Commit `f5c54b17b2b04be8a97d88ae4ce295a5559f9e5a`. PowerShell suite now contains **14 authored tests** (including an intentionally overlapping denied-read assertion for ordering coverage); Bash suite remains **14 authored tests**. **Source-only change, not executed:** no runtime PASS, link-audit PASS, OCP 4.22 lab result, independent review or production approval claimed. Next: run offline suites in a credential-isolated checkout and record actual outcomes before further test expansion.


## V06 offline test result integrity gate — 2026-11-20

Reviewed the V06 execution protocol for false-positive validation reporting. Added mandatory reconciliation of `unittest` discovered test counts and skip counts with the pinned source revision; a zero-test discovery is **BLOCKED**, and an entirely skipped PowerShell suite is **SKIP**, never PASS even with exit code zero. Documented immediate shell exit-code capture for Bash and PowerShell and explicitly classified unavailable checkouts as **BLOCKED / NOT RUN**. Current authored expectations: **14 Bash and 14 PowerShell** identity-guard tests, subject to recount at execution SHA. Commit `2d6cb8c7b1db4e9cd2d34e912c5495fb6a159daa`. GitHub checkout attempted during this review but failed DNS resolution for `github.com`; no offline suites, Markdown auditor, or cluster tests were executed. No independent review or production approval. Next: obtain a complete isolated checkout, run the suites, reconcile counts and sanitized evidence, and correct actual failures.

## V06 offline evidence capture correction — 2026-11-20

Clarified that piping test output through `tee` can mask failures; added Bash and PowerShell examples that capture output outside the repository and preserve native exit codes, with explicit treatment of missing `Ran N tests` summaries and raw-log sanitization. This is documentation-level protocol hardening, **not** test execution. The 14 Bash and 14 PowerShell authored tests, other offline regression suites, full Markdown audit, isolated OCP 4.22 validation and independent technical approval remain pending.

## V06 Bash evidence formatting correction — 2026-11-20

Reviewed the executable Bash evidence-capture example and corrected a double-escaped `printf` newline that would print a literal `\n` rather than a line break. Commit `8760dea34067cad0df13d7cf510c36f475356f36`. This is a verified source-level correction, **not** evidence that regression suites ran. The 14 Bash and 14 PowerShell authored tests, other offline suites, Markdown audit, isolated OCP 4.22 runtime validation and independent review remain pending. Next: obtain a credential-isolated checkout and execute all offline checks, preserving actual exit codes and test counts.

## V06 PowerShell ordered-command assertions — 2026-11-20

Strengthened the existing 14-case PowerShell identity-guard suite: the authorized-read scenario now checks the **complete ordered 12-command trace**, not just a count of four reads; the explicit-denial scenario now checks the **ordered four RBAC queries** and absence of resource reads. This closes a false-positive gap where an unexpected or missing diagnostic step could still satisfy the previous count-only assertions. Commit `5935f5ab89ef057367717a2f97047ea835ddfce6`. **Authored and GitHub-source-verified only**; local Git checkout still cannot resolve `github.com`, so no test suites or link auditor were executed. All 18 chapters remain drafted, not lab-tested or production-approved. Next: execute offline regression suites in a credential-isolated checkout and reconcile actual counts, exits and skips.


## V07 — Recovery acceptance evidence gates (2026-11-20)

Added [V07 etcd and stateful recovery acceptance worksheet](validation/V07-etcd-and-stateful-recovery-acceptance.md) covering version/topology compatibility, snapshot/static-resource pairing, app data boundaries, restore integrity, RPO/RTO, security approvals, stop conditions and independent acceptance. **Documentation drafted only; no backup, restore, offline suite, live OCP test or independent review executed.** All 18 chapters remain drafted and not production-approved.

## V07 — Measured recovery evidence template (2026-11-20)

Extended the existing V07 worksheet with an isolated-rehearsal timestamp template, per-service RPO/RTO definitions, NOT MEASURABLE handling, and an explicit change-control boundary. Commit `c7a31345059d5af51cf3b1cf196ee4b2e480d597`. **Source authored only; no recovery exercise, runtime test, independent review, or production approval performed.** Next: execute credential-isolated offline suites, then obtain version-specific independent recovery review.

## V07 Chapter 015 recovery lab identity safety review — 2026-11-20

Corrected Lab 015's read-only preflight to fail closed before any resource authorization or reads when `oc whoami`, current-context, API server lookup, or `oc version` fails. Bash requires `EXPECTED_API_SERVER` and PowerShell requires `$ExpectedApiServer`, both sourced from a separately approved non-secret cluster record; an empty or mismatched API URL stops the lab. Do not publish the URL in shared evidence. Commit `b4ffcf06e06f29c60d0dbd977d3ff1ed89847011`. **Source-level documentation review only**; neither shell was executed against an OpenShift cluster and no test PASS, independent review or production approval is claimed. Next: run isolated mock-based preflight regression tests, check PowerShell/Bash failure handling, then complete offline suite and link audit.

## V07 Lab 015 identity guard regression design — 2026-11-20

Corrected literal escaped newline formatting in Lab 015's identity/RBAC guidance and added [isolated Lab 015 regression cases](validation/V07-lab015-identity-guard-regression-cases.md). The 12-case matrix covers identity lookup, context/server/version failure, authorization denial/ambiguity, unexpected commands, failed reads and PowerShell nonzero exit with misleading output. It flags that the current examples do not explicitly check every authorization exit status and must not be considered fully fail-closed or recovery-ready without mock-based execution. **Documentation and test-design only; no tests or OCP commands executed.** Next: implement and execute mock tests in a credential-isolated checkout, record actual evidence, and correct confirmed failures. Independent review and production approval remain pending.

## V07 Lab 015 authorization/read failure reporting — 2026-11-20

Updated [Lab 015](labs/015-recovery-read-only-readiness-audit.md) to inspect authorization command exit codes in both Bash and PowerShell, distinguish explicit denial (SKIP) from failed authorization (UNKNOWN/ERROR), and surface failed resource reads as incomplete evidence rather than successful readiness. Commit `dd3f775b520e34ad0cf977473e47221c325ca9f8`. **GitHub source change only:** neither shell nor any mock tests were executed; the PowerShell helper's output and parameter binding and Bash status propagation require isolated regression verification. A SKIP still prevents full recovery-readiness certification. No cluster tests, independent approval or production certification. Next: implement the 12-case V07 mock suite, run it offline, fix confirmed failures, then audit links and OCP 4.22-specific recovery semantics.

## V07 Lab 015 PowerShell argument binding and evidence-output correction — 2026-11-20

Reviewed the current Lab 015 Bash/PowerShell helper source. Replaced ambiguous positional PowerShell array arguments with explicit `-PermissionArgs` and `-ReadArgs`, suppressed potentially unsanitized resource output from the status helper, and made Bash authorization arguments an explicit fixed array (no `eval`). Commit `010c35366101fc16894b27b1ec3bc197de48b1b3`. **Source change verified by GitHub re-fetch; no offline mock execution, cluster lab, link audit, independent review or production approval performed.** Next: execute mock regression cases, verify PowerShell native command exit status and Bash SKIP/ERROR propagation, and capture sanitized actual results.

## V07 Lab 015 offline source-contract regression checks — 2026-11-20

Added `validation/test_lab015_readiness_contract.py` (commit `85b95e1623554f0a097b717014be8b0295728061`), seven Python standard-library `unittest` cases checking identity-preflight order, authorization failure handling, four resource/permission pairs and absence of selected mutating/credential-exposing commands in the Bash and PowerShell lab examples. Run with `python -m unittest discover -s openshift/validation -p 'test_lab015_readiness_contract.py' -v` (Windows: `py -3 -m unittest discover -s openshift/validation -p 'test_lab015_readiness_contract.py' -v`). These are **static source-contract tests only**, not executable mocked `oc` tests, complete semantic analysis or cluster validation. **No tests were executed in this GitHub-only editing session.** Next: run these seven tests in an isolated checkout, implement mocked exit-code/argument tests, run the previously authored Bash/PowerShell suites, and record actual evidence before any validation status changes.

## V07 Lab 015 output-redaction source correction — 2026-11-20

Corrected the Bash read helper to suppress successful resource output (`>/dev/null`), matching PowerShell behavior, and documented that stderr may still contain sensitive infrastructure identifiers. Added an eighth static source-contract check for Bash output suppression. **GitHub source changes only; tests were not executed.** Mocked `oc` exit-code tests, full offline suites, link audit, isolated OCP 4.22 validation and independent security approval remain pending. Do not share raw terminal transcripts or claim recovery readiness from these checks.

## V07 Lab 015 isolated Bash mock harness — 2026-11-20

Added [test_lab015_bash_mock.py](validation/test_lab015_bash_mock.py) with six Python `unittest` cases that execute the Bash lab snippet against a temporary fake `oc` on PATH. Scenarios: authorized reads, identity failure, API-server mismatch, four explicit RBAC denials, authorization command failure, and resource-read failure. Mock command traces verify that preflight failures do not reach resource reads, denials skip reads, and errors mark the audit incomplete. The harness needs Python 3 and Bash; it does not contact a cluster or require credentials. Run `python -m unittest discover -s openshift/validation -p 'test_lab015_bash_mock.py' -v` in a credential-isolated checkout. **Authored and GitHub-source-verified only; no local execution or PASS asserted.** PowerShell mock execution, the earlier regression suites, Markdown audit, isolated OCP 4.22 tests, and independent approval remain pending. Next: execute this suite and fix observed failures before extending PowerShell parity.

## V07 Lab 015 PowerShell mock harness — 2026-11-20

Added [test_lab015_powershell_mock.py](validation/test_lab015_powershell_mock.py) with six isolated PowerShell 7 mock cases: successful read-only checks, identity failure, API-server mismatch, RBAC denial, authorization failure, and resource-read failure. The harness shadows `oc` with a PowerShell function, records arguments to a temporary file, and does not require credentials or a cluster. Execute with `python -m unittest discover -s openshift/validation -p 'test_lab015_powershell_mock.py' -v`; hosts without `pwsh` skip. **Authored only; not executed or certified.** Validate on Windows PowerShell 5.1 separately, then run all offline suites and record genuine PASS/FAIL/SKIP evidence before any readiness claim.

## V07 Lab 015 version-preflight mock coverage — 2026-11-20

Extended both existing isolated Lab 015 mock suites with a `version_fail` scenario (mock exit 13), asserting a nonzero script result, exactly one version check, no subsequent authorization or resource reads, and the expected STOP diagnostic. Bash and PowerShell now each define seven mock scenarios (14 total). This verifies a test *expectation in source*, not an executed PASS: **no test execution or OCP cluster access occurred in this GitHub editing session**. Next: run the suites in a credential-isolated checkout, record individual PASS/FAIL/SKIP outcomes, investigate failures, then run the earlier offline checks and Markdown link audit. Independent review and production approval remain pending.

## V07 Lab 015 mock subprocess credential-isolation correction — 2026-11-20

Reviewed both seven-case Lab 015 mock harnesses and found that they inherited the parent process environment wholesale. That could expose `KUBECONFIG`, cloud credentials, proxy secrets or other tokens to test subprocesses even though `oc` was mocked. Changed the Bash harness to use a minimal PATH (`temporary fake oc` plus system default paths), temporary HOME/TMPDIR and no inherited credentials; changed the PowerShell harness to use an explicit environment allowlist (PATH plus temporary HOME/USERPROFILE/TMP/XDG_CONFIG_HOME and mock-only variables). The PowerShell host executable remains explicitly resolved, and both harnesses continue to target a fake `oc`. Commits `95c5bb3d292cb59b5be1f0423773f6c706f1fce6` and `c98e693b88053087b44b85e913361e1db28d2571`. **GitHub source changes only; no subprocess test execution or PASS claimed.** A local checkout was blocked by DNS resolution of github.com; independently verify Bash/PowerShell startup with the restricted environment and run all 14 mock cases before treating isolation as validated. The PowerShell PATH is inherited to permit host startup, so test execution should still occur in a controlled isolated runner with no real cluster credentials. No OCP cluster access, independent review or production approval occurred.

## V07 Lab 015 Bash mock credential-inheritance guard — 2026-11-20

Added a Bash mock regression case that plants synthetic `KUBECONFIG`, `AWS_SECRET_ACCESS_KEY`, and `OC_TRACE` variables in the parent process while running the isolated Lab 015 helper. The fake `oc` now exits 97 if kubeconfig or AWS secret variables reach it, so a future accidental environment inheritance fails the success scenario. Commits `09ee8340591c734d6ec0715bae1b9235eea9746e` and `78a16d20880fa82ebecbf3177066b834de6f0a2c`. Bash mock coverage is now eight cases; PowerShell remains seven (15 combined). **Tests authored and source-verified on GitHub, not executed; no PASS claimed.** Next: execute mock suites in a credential-isolated checkout, fix failures, add PowerShell environment leakage assertion, audit links and obtain independent review. No live OCP cluster access or production approval.

## V07 Lab 015 PowerShell mock credential-inheritance guard — 2026-11-20

Added an eighth PowerShell mock case using synthetic parent `KUBECONFIG`, `AWS_SECRET_ACCESS_KEY`, and `AZURE_CLIENT_SECRET` values. The fake `oc` throws if these variables reach its subprocess; the new case expects all four read-only resource checks to complete without leakage. PowerShell mock coverage is now eight cases, matching eight Bash cases (16 authored scenarios total). Source change committed as `d2d063768f6026f613ab15a15a28010d5671cfff`. **Not executed:** no PASS/FAIL claim, no real cluster access. Next: execute both isolated mock suites, verify restricted PowerShell startup and fail-path behavior, then perform link/security audits and independent OCP 4.22 review. Production approval remains pending.

## V07 Lab 015 Bash output and command safety regression additions — 2026-11-20

Added two Bash mock scenarios in `validation/test_lab015_bash_mock.py`: successful diagnostics must not expose the mocked identity, context or version in stdout, and every observed `oc` invocation must match a restricted read-only command allowlist. Bash coverage is now **10 authored scenarios**, PowerShell remains **8** (18 combined). Commit `355ae8fa2776420ba016f0bd0e582539072acf18`. **Not executed:** the local GitHub checkout failed DNS resolution (`Could not resolve host: github.com`), so these checks are authored/source-reviewed only, not PASS. Run the suites in a clean isolated checkout, inspect genuine failures, and record evidence before upgrading any validation status. Independent OCP 4.22 review and production approval remain pending.


## V07 Lab 015 Bash resource-output assertion repair — 2026-11-20

Corrected a false-negative in `validation/test_lab015_bash_mock.py`: the fake `oc get` previously returned an empty payload, so the existing output-suppression test could pass even if the lab printed fetched resources. The fake now emits `SENTINEL_CLUSTER_RESOURCE_PAYLOAD_DO_NOT_EMIT` for successful resource reads, and the test asserts this marker is absent from both stdout and stderr. This strengthens an existing test without adding a duplicate scenario. Commit `202340f37a9d8d385130ecb26c7d6da9e9f76add`. **Status: authored, not executed** because the local GitHub checkout still fails DNS resolution; no PASS, live OCP validation or production approval claimed. Next: execute all 18 Bash/PowerShell mock scenarios in an isolated checkout, preserve sanitized results, and fix confirmed failures.

## V07 Lab 015 PowerShell resource-output regression — 2026-11-20

Updated `validation/test_lab015_powershell_mock.py` so successful fake `oc get` calls return a synthetic `SENTINEL_CLUSTER_RESOURCE_PAYLOAD_DO_NOT_EMIT` marker. Added a ninth PowerShell scenario asserting that neither stdout nor stderr contains the marker, closing the analogous false-negative already corrected in Bash. Commit `5db86b12ced9a8621fe9b500c147396dea59df11`. **19 authored mock scenarios total (10 Bash, 9 PowerShell); not executed and no PASS claimed.** Next: execute suites in a credential-isolated checkout, record sanitized results, audit links and seek independent OCP 4.22 review. No production approval.

## V07 Lab 015 offline execution protocol — 2026-11-21

Added [Lab 015 offline execution and evidence plan](validation/LAB-015-OFFLINE-EXECUTION-PLAN.md), with credential-free prerequisites, Bash/PowerShell 7 commands, genuine PASS/FAIL/ERROR/SKIP recording, security-stop conditions, and independent-approval boundaries. Commit `36bc58887ef1dccd1efb65e7c0968a950964b6c7`. **Documentation-only change; 19 mock scenarios remain authored but not executed.** Next: run both suites on an isolated runner and record actual sanitized evidence; then address failures and perform OCP 4.22 cluster validation under separate authorization.

## V07 Lab 015 PowerShell command allowlist regression — 2026-11-21

Added an offline PowerShell mock regression that compares the successful Lab 015 `oc` command trace against an exact twelve-command read-only allowlist (identity, context, API server, version, four authorization checks and four resource reads). It also explicitly rejects common state-changing command prefixes. This complements the existing Bash command-safety coverage and raises the authored Lab 015 mock count to **20** (10 Bash, 10 PowerShell). **GitHub source committed; test not executed**: no PowerShell runtime PASS/FAIL evidence or live cluster validation is asserted. Next: execute both isolated suites and record sanitized PASS/FAIL/SKIP evidence, then address any failures. Independent review and production approval remain pending.

## V07 draft PR scope and release-gate reconciliation — 2026-11-21

PR #1 was merged; the active validation branch is `docs/openshift-ch010-security-governance` in draft PR #2. Although PR #2 was originally titled for Chapter 010, it now contains subsequent Chapter 011–018 drafts and validation work. Review the **entire current PR diff**, not just Chapter 010, before considering merge. Do not interpret a green GitHub mergeability flag as technical acceptance.

**Current evidence boundary:** All 18 chapters are documentation-drafted; none is cluster-lab-verified, independently technically approved, or production-certified. The Chapter 015 Bash/PowerShell mock scenarios are *authored*, not runtime-passed. No live cluster, backup restoration, upgrade, node drain or stateful failover was performed for this milestone.

**Pre-merge checklist:** (1) enumerate changed paths and confirm they are confined to `openshift/` (except any explicitly approved minimal root README link); (2) run local Markdown relative-link and security scans with recorded command, environment and exit status; (3) execute isolated Bash and PowerShell mock harnesses, capturing per-case PASS/FAIL/SKIP and sanitized evidence; (4) verify OCP 4.22-sensitive commands and APIs against official Red Hat documentation; (5) obtain independent platform/security review of RBAC/SCC, upgrade, etcd and stateful-HA procedures. Any failed gate blocks promotion of the relevant procedure to production-approved status. Do not merge automatically.

**Next:** Execute the existing Chapter 015 mock suites in a credential-isolated checkout; attach sanitized, reproducible evidence and repair observed failures before adding further scenarios.

## V08 PR #2 changed-path inventory — 2026-11-21

GitHub PR changed-file inventory inspected against the active draft PR #2 (head: `docs/openshift-ch010-security-governance`, base: `main`). **71 changed paths** were returned; **all 71 are under `openshift/`**, with no root README, `kubernetes/`, or other repository paths changed. The changed-path list contains **17 chapter Markdown paths (002–018)** with no repeated exact path; Chapter 001 belongs to merged PR #1. This is a **GitHub metadata/source-scope check only**, not an offline checkout audit, a semantic duplicate-content review, a Markdown-link PASS, a security scan, or a runtime test. The PR remains draft and unmerged.

**Next validation gate:** execute the existing link/security checks and Lab 015 Bash/PowerShell mock suites in a clean credential-isolated checkout; record real commands, environment, exit codes and sanitized per-case evidence. A source-only inventory must not be reported as runtime validation or production certification.

## V08 — Markdown link-checker regression fixture correction (2026-11-21)

Corrected `validation/test_check_relative_links.py` so the invalid backtick-fence info-string scenario writes three actual Markdown lines instead of literal `\\n` sequences. This makes the intended regression meaningful: the invalid opener must not hide a missing link on the following line. Source inspection and GitHub commit verification completed; **the Python test suite and repository-wide link audit have not been executed in this run**. Next: run `python -m unittest discover -s openshift/validation -p 'test_*.py'` in a clean checkout, record actual results, and fix any failures before claiming V08 PASS. No OCP cluster was accessed.


## V01 link-validator regression coverage — 2026-11-21

Added two offline regression fixtures for percent-encoded local filenames with query/fragment suffixes and tilde-fenced code containing a mismatched backtick fence. These protect against false missing-link reports and accidental suppression of a broken link after a valid fence closes. Test changes committed as `65369f52edfc785f250ac774d8f8a03524f23e26`. The GitHub checkout remains unavailable in this execution environment (DNS resolution of github.com failed), so these tests were **authored but not executed**; neither the full link audit nor a runtime PASS is claimed. Next: run Python unittest discovery and the complete relative-link audit in a credential-isolated checkout, record genuine results and fix confirmed defects. OCP cluster testing and independent approval remain pending.


## V01 missing-target URL normalization regression — 2026-11-21

Added two offline regression cases for **missing** percent-encoded Markdown targets with query/fragment suffixes, covering both inline links and reference definitions. These complement the existing valid-target fixture and guard against false PASS when URL decoration obscures an absent local file. Source authored and committed as `60abf9e047e7437702a126c7d1f0aa157223713c`. **Not executed:** the local checkout still cannot resolve github.com; no Python unittest, full link audit, OCP cluster validation or production approval is claimed. Next: run Python unittest discovery and the full offline link checker in a clean credential-isolated checkout, record exit codes and sanitized output, and correct any confirmed failures.


## V01 absolute-path portability regression — 2026-11-21

Corrected `validation/check_relative_links.py` to reject absolute filesystem paths (POSIX and Windows drive paths) as nonportable local Markdown targets, even when the target exists on the executing host. Added a temporary-directory regression proving an existing absolute target must fail. This does not prohibit intentional relative links to the sibling `kubernetes/` learning path. GitHub source commits: `9fc88276fee166278fed4600188d890460d79588`, `76b1c202c82e91317d18e1ad34af9e1ca86f25ea`. **Source change only, not runtime-verified**: the checkout still fails GitHub DNS resolution; execute Python unittest discovery and the complete link audit in a clean isolated checkout before recording PASS. No OCP cluster accessed or production approval granted.

## V07 Windows-path link audit hardening — 2026-11-21

Corrected the Markdown link validator so Windows drive-letter paths (for example `C:/private/secret.md`) are not mistaken for external URL schemes and silently skipped. Added an offline regression test asserting an absolute-local-path failure. Preserved legitimate relative cross-track references such as `../kubernetes/` by removing an overrestrictive audit-root containment check during the same review. Changes are committed to the existing draft PR branch. **Validation: source changes and GitHub commits verified; Python test execution not performed because local GitHub checkout fails DNS resolution.** No OCP cluster access, independent review or production approval occurred. Next: run offline Python tests and complete the link audit with genuine evidence.

## V08 — Credential-isolated offline validation execution checklist (2026-11-21)

Added [offline execution checklist](validation/OFFLINE-EXECUTION-CHECKLIST.md) documenting clean-checkout identity, credential isolation, Python unittest execution, discovery of current Chapter 015 mock-suite entry points, real exit-code evidence, PASS/FAIL/SKIP/NOT RUN distinctions and escalation gates. This is **documentation only**. The local GitHub checkout still fails DNS resolution, so Python and Bash/PowerShell suites, repository-wide Markdown link audit, isolated OCP 4.22 runtime testing and independent approval remain **NOT RUN/PENDING**. Next: execute in a credential-isolated environment, preserve sanitized evidence and correct confirmed defects. No production changes or merges.


## V01 link containment hardening — 2026-11-21

Corrected the offline Markdown link checker to reject relative paths that resolve outside the permitted repository boundary, even when the target exists on the host. The default `openshift/` audit permits cross-track references to sibling `kubernetes/` within the repository, without modifying Kubernetes files. Added a regression fixture for an existing out-of-root file. Commits: `bcf0483`, `bcc9016`, `a888a59`. **GitHub source/commit verification only:** Python tests and full link audit have not been executed, and no cluster or production testing is claimed. Next: execute unittest discovery and complete the link audit from a credential-isolated checkout, review any failures, then run Chapter 015 offline mock suites.

## V01 repository-boundary guard syntax repair — 2026-11-21

Inspected the actual draft branch validator and found literal `\\n` sequences embedded inside the Python comment/guard block. This caused the intended `repository_root` assignment and boundary check to be swallowed by a comment, leaving `if not resolved.exists()` outside the intended guard and making path-escape protection ineffective. Replaced the literal escape sequences with actual newlines in `validation/check_relative_links.py` (commit `39720745fe2bbe4b1667f4ae653b7322f4e6ce34`). This is a source-level correction verified through GitHub content inspection; **Python compilation, regression execution, full Markdown audit, isolated cluster tests and independent review are still pending**. Next: run `python -m unittest discover -s openshift/validation -p 'test_*.py'` and `python openshift/validation/check_relative_links.py` in a complete isolated checkout; capture exit codes and sanitize evidence before marking any checks passed.

## V01 path-containment regression expansion — 2026-11-21

Added two offline Python regression cases for (1) a symlink inside the audit root that resolves to a real file outside the repository boundary and (2) a legitimate relative reference from `openshift/` to the existing sibling `kubernetes/` track. The symlink test skips on hosts without symlink creation permissions. These cases protect both security containment and allowed cross-track navigation; they do **not** alter Kubernetes content. Commit: `9cfa411aba3165b8538f6877024c6bbadd4e1558`.

**Execution status:** Test source committed; neither case has been executed. The isolated runner cannot resolve `github.com` for a complete checkout. Python compilation, regression discovery, full Markdown link audit, Chapter 015 Bash/PowerShell mock scenarios, live OCP 4.22 validation, and independent production approval remain pending. Next: run the existing offline suites in a credential-isolated full checkout and record sanitized command/exit-code evidence; fix observed failures before promotion.


## Offline link audit regression extension — 2026-11-21

Added two unexecuted Python regression scenarios for percent-encoded parent traversal (`%2e%2e/`) and encoded absolute paths (`%2F`). Both assert that local-link validation rejects nonportable or out-of-bound targets. GitHub source was committed; local Python execution, full link audit, Chapter 015 mock suites, OCP 4.22 cluster validation, and independent technical approval remain pending. Do not report PASS until actual exit codes and sanitized logs are captured.

## V01 file-URI link audit hardening — 2026-11-21

Identified a source-level bypass: the Markdown link validator treated `file:` links as external schemes, allowing host-local file URIs to escape the portable-link audit. Updated `validation/check_relative_links.py` to reject `file:` URLs explicitly, including mixed-case schemes. Added two regression fixtures: an existing local file referenced by `Path.as_uri()` and a mixed-case `FiLe:` URI. Source changes committed on the existing draft PR branch. **Not executed:** Python compilation, regression tests, repository-wide link audit, Chapter 015 mock suites and isolated OCP 4.22 runtime validation. These remain NOT RUN, not PASS. No production access or approval. Next: execute offline suites in a complete credential-isolated checkout, capture genuine exit codes, correct failures and obtain independent review.

## V01 unsafe Markdown URI scheme review — 2026-11-21

Source inspection identified that the link checker skipped executable or embedded URI schemes (`javascript:`, `data:`, `vbscript:`) as if they were ordinary external documentation links. The checker now rejects these schemes as well as `file:` URIs; existing file-URI tests were updated for the revised diagnostic and a parameterized regression case was added. Source changes committed to the existing draft PR branch. **Validation boundary:** GitHub source/commit inspection only; Python tests and the full Markdown audit were NOT RUN, and the new cases are not reported as passing. Next: execute unittest discovery and the complete audit in a credential-isolated checkout; repair any failures before review. No live cluster access, production approval or merge.
