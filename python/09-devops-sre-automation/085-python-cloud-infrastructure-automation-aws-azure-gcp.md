# Chapter 085 — Python Cloud Infrastructure Automation with AWS, Azure and GCP

**Part 09 — DevOps, SRE and Automation · Chapter 085/120 · Python 3.11+**

## Learning outcomes

Implement safe, read-only multicloud inventory automation using AWS boto3, Azure Resource Management SDK, and Google Cloud Resource Manager SDK. Explain identity, API pagination, throttling, bounded retries, regional and project scope, idempotency, dry-run and operational auditing. Build and test a **credential-free, mocked** SRE/DBRE lab before opting into live inventory.

[Chapter 085 hands-on lab](labs/085-multicloud-inventory-automation-sre-devops-dbre-lab.md) | [Executable project directory](labs/085/README.md)

## 1. Architecture

\`\`\`text
Operator / CI with least-privilege identity
    -> CLI (provider, scope, dry-run, page/record budgets)
    -> provider adapter (AWS / Azure / GCP)
    -> SDK credential chain + endpoint policy
    -> paginated, bounded inventory
    -> canonical normalized records + stable deduplication
    -> redacted structured report / metrics / change evidence
    -> approval-gated remediation (OUT OF SCOPE for lab)
\`\`\`

Inventory is not remediation. Treat every account, subscription, project and region as an explicit scope boundary. Do not automatically delete, restart or mutate cloud resources based on inventory findings.

## 2. AWS boto3

\`boto3.Session(profile_name=..., region_name=...)\` uses the standard AWS credential-provider chain; in CI prefer role assumption or workload identity instead of long-lived static access keys. Verify the AWS account with STS \`GetCallerIdentity\` when permitted, and scope the role's IAM policy to the required read operations. EC2 \`describe_instances\` supports \`NextToken\` pagination and \`MaxResults\` with caveats depending on filters. The lab enumerates EC2 instance IDs using the \`describe_instances\` paginator. Real AWS quotas and throttling differ by API. Set \`botocore.config.Config(retries={"mode":"standard","max_attempts":3},connect_timeout=...,read_timeout=...)\` and understand that SDK retries are already enabled; avoid stacking unbounded application retries.

## 3. Azure SDK

Use \`DefaultAzureCredential\` locally or in approved workloads; in production prefer a managed identity or federated workload identity with a narrow \`Reader\` assignment. \`ResourceManagementClient(credential, subscription_id)\` can enumerate resources through \`resources.list()\`, which returns a paged iterable. Azure \`DefaultAzureCredential\` can try multiple identities; configure and audit the intended identity rather than accidentally using a developer login in CI. Subscription and tenant boundaries must be verified separately. Respect \`Retry-After\`, SDK retry configuration and per-subscription throttling.

## 4. Google Cloud SDK

Use Application Default Credentials with Workload Identity Federation or attached workload identity; avoid exported service-account keys. The \`google-cloud-resource-manager\` v3 \`ProjectsClient\` supports \`search_projects\` with a \`SearchProjectsRequest\` and iterable pager. Project search visibility depends on caller permissions and hierarchy. **This lab uses project inventory rather than VM inventory on GCP**; normalize record types accordingly. Use \`google.auth.default()\` for identity troubleshooting without printing tokens. Set per-call timeouts and API retry policies and test organization/folder visibility.

## 5. Pagination, memory and consistency

Cloud inventory APIs are eventually consistent and pages may change during a scan. Use paginators or iterators; enforce a maximum record budget, not only a page budget. Deduplicate by a stable provider-qualified resource key and record scan start/end times. Avoid collecting an entire organization into memory. A \`max_records\` cap produces a **partial** result and must be clearly labeled as such; never present it as a complete inventory. For massive fleets stream normalized JSON Lines to an approved sink with bounded buffers and checkpointing.

## 6. Retries and rate limiting

Handle throttling, transient 5xx and connection timeouts with capped exponential backoff and jitter, a total request deadline, and respect provider \`Retry-After\` guidance. Avoid retrying invalid credentials, authorization failures, malformed scope, or schema errors. SDKs already retry some failures. Prefer a single coordinated retry budget across layers; track retries, throttling and latency by provider. Limit concurrency by account, subscription or project rather than globally assuming unlimited quotas.

## 7. Idempotency and dry-run

Read-only inventory is naturally non-mutating but not necessarily repeatable: resources change. Dry-run must describe intended provider, scope and record budget **without making network calls**. For future write automation, require a desired-state diff, explicit approval, immutable change ID, precondition checks, provider-native conditional operations, reconciliation after ambiguous timeouts and a rollback plan. Do not equate a retry-safe HTTP method with an exactly-once workflow.

## 8. Security

- Never embed credentials in code, config files, CLI arguments, logs or GitHub Actions output.
- Restrict cloud roles to read-only inventory for this lab. Verify tenant/account/project scope.
- Use approved TLS trust roots, endpoint validation and workload identities.
- Do not print resource tags, metadata or names without checking sensitivity; this lab prints only selected identifiers.
- Do not enable broad organization discovery unless explicitly approved.
- Record who ran the scan, what scope was approved, what was returned, and whether results are partial.

## 9. SRE/DBRE applications

**AWS/EKS/RDS/MSK:** inventory EC2 nodes, tags and account boundaries before maintenance; add service-specific adapters for RDS or MSK rather than treating EC2 enumeration as full infrastructure coverage.

**Azure/AKS:** enumerate scoped Azure Resource Manager resources, reconcile resource group ownership and planned maintenance windows.

**GCP/GKE:** enumerate visible projects before expanding to Compute Engine, GKE or Cloud SQL; project visibility does not imply access to every service.

**FinOps:** join normalized inventory with separately authorized billing exports, ownership metadata and retention policies. Do not infer cost solely from resource count.

## 10. Troubleshooting

| Symptom | Likely cause | Response |
|---|---|---|
| AWS AccessDenied | IAM policy, SCP, wrong role/account | Check caller identity and approved role; do not bypass |
| Azure 403 | Wrong tenant, subscription or RBAC | Check token audience and Reader scope |
| GCP PermissionDenied | IAM role or hierarchy visibility | Verify ADC identity and project search permissions |
| Missing resources | Pagination, filters, eventual consistency | Check scan completeness and next tokens |
| 429/Throttling | Too much concurrency | Respect Retry-After, cap scan rate |
| Expired token | Identity provider/rotation | Refresh credential through supported chain |
| Partial inventory | Record budget exhausted | Mark partial; resume in approved window |
| Duplicate records | Page overlap or eventual consistency | Deduplicate by provider-qualified ID |
| Long scan | Large fleet or slow API | Use bounded timeouts, streaming and checkpoints |

## 11. Incident simulations

1. AWS wrong account; 2. Azure wrong subscription; 3. GCP missing project visibility; 4. expired credential; 5. permission denied; 6. AWS throttling; 7. Azure 429; 8. GCP 503; 9. connection timeout; 10. page overlap; 11. missing next token; 12. record budget exceeded; 13. partial result misreported as complete; 14. duplicate resource ID; 15. invalid region; 16. malformed resource object; 17. cloud API schema change; 18. SDK retry amplification; 19. secret leaked in exception; 20. unexpectedly large resource group; 21. IAM scope escalation; 22. concurrent scan overload; 23. API endpoint/TLS failure; 24. inventory drift during maintenance.

## 12. Runbooks

**Preflight:** identify account/subscription/project, approved identity, region and record budget. Run dry-run, then check caller identity and permission scope before live collection.

**Throttling:** stop parallel scans, inspect SDK retry metrics and provider headers, lower concurrency and reschedule.

**Authorization:** do not retry 401/403 indefinitely. Confirm identity, tenant and least-privilege role; escalate to resource owner.

**Partial inventory:** label output partial, retain scan scope/time and deduplication key, and request another authorized window.

**Incident/rollback:** disable automation, revoke compromised credentials, preserve sanitized audit evidence and revert only through approved infrastructure-as-code changes.

## 13. Lab, validation and assessment

The [lab](labs/085-multicloud-inventory-automation-sre-devops-dbre-lab.md) provides **standalone** Python modules, requirements, deterministic fake SDK clients, unit tests, a CLI and a 100-point assessment. It exercises real boto3/Azure/GCP adapter call shapes against mocked clients, without cloud credentials. Live provider integration is optional and not executed by publication. **Next proposed:** Chapter 086 — Python Kubernetes and Container Automation.
