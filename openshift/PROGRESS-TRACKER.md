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
