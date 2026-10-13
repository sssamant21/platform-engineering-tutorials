# Chapter 049 — Certificate Management and Rotation

**Track:** Kubernetes Administration · **Part 10 — Node Operations and Troubleshooting**  
**Status:** Draft — runtime validation and technical review pending  
**Audience:** SRE, DBRE, Kubernetes administrators, platform engineers

## 1. Production scenario
An admission webhook's TLS certificate is renewed, but the API server rejects new Pods with an unknown-authority error. Separately, a kubelet client certificate approaches expiry. Investigate ownership, expiry, trust, SANs and safe rotation without disabling TLS verification or weakening admission controls.

**Learning objectives:** map Kubernetes PKI, inspect public certificates and CSRs, distinguish leaf renewal from CA rotation, assess provider ownership, monitor expiry, troubleshoot x509 errors, and execute a staged rotation runbook.

## 2. PKI and trust boundaries

```text
API server serving certificate -> kubectl, controllers and clients
Kubelet client certificate -> API server client authentication
etcd peer/client/server certificates -> etcd cluster and API server
Admission webhook serving certificate -> API server trusts caBundle
Ingress/application certificate -> external/internal clients
Cloud workload identity OIDC tokens -> separate from X.509 rotation
```

| Certificate | Typical owner | Key risk |
|---|---|---|
| API server TLS | Managed provider or control-plane administrator | API outage and client trust |
| etcd peer/client/server | Control-plane/etcd administrator | Quorum and storage availability |
| Kubelet client | Kubelet and CSR signer/approver | Node authentication |
| Admission webhook TLS | Webhook operator | New workload admission failures |
| Ingress/application TLS | Application/platform team | Client handshake failures |
| Service mesh mTLS | Mesh operator | Service-to-service trust failures |

**Important:** a leaf certificate renewal is not equivalent to rotating a certificate authority. CA rotation requires identifying all relying parties, staging overlapping trust where supported, and coordinating cutover.

## 3. Lab safety and setup

All core labs are read-only. Never print private keys, kubeconfig client key data, bearer tokens or TLS Secret key material. Use Windows PowerShell and an approved context.

```powershell
kubectl config current-context
kubectl version
kubectl cluster-info
kubectl auth can-i list certificatesigningrequests.certificates.k8s.io
kubectl auth can-i list validatingwebhookconfigurations.admissionregistration.k8s.io
```

## 4. Lab 1 — Inventory API endpoint and CA configuration

```powershell
$server = kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
$caData = kubectl config view --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}'
$caPath = kubectl config view --minify -o jsonpath='{.clusters[0].cluster.certificate-authority}'
Write-Output "API endpoint: $server"
Write-Output "Embedded CA configured: $([bool]$caData)"
Write-Output "CA file configured: $([bool]$caPath)"
Remove-Variable caData
```

**Expected:** identify API endpoint and trust configuration without exposing authentication material. Some clusters use provider-managed authentication or different kubeconfig formats. Do not run `kubectl config view --raw` in tickets or logs.

## 5. Lab 2 — Inspect public certificate expiry, SAN and issuer

On a machine with OpenSSL and connectivity to the authorized API endpoint:

```powershell
$uri = [uri]$server
$hostName = $uri.Host
$port = if ($uri.IsDefaultPort) { 443 } else { $uri.Port }
'' | openssl s_client -connect "${hostName}:$port" -servername $hostName -showcerts 2>$null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

**Expected:** subject, issuer, notBefore, notAfter and SANs for the presented certificate. This inspection alone does **not** verify the full trust chain; validate with the approved CA and hostname checks separately. Private endpoints may require a bastion or provider tooling. Never use insecure TLS options as a fix.

## 6. Lab 3 — Inspect kubelet CSRs and approval workflow

```powershell
kubectl get csr
kubectl get csr -o custom-columns=NAME:.metadata.name,SIGNER:.spec.signerName,USER:.spec.username
kubectl get nodes -o wide
```

**Expected:** CSR inventory, possibly empty if no requests are pending. Pending requests require identity verification and signer/approver review. Approved-but-not-issued requests require signer investigation. Never blindly approve all CSRs: they can grant powerful client identities.

## 7. Lab 4 — Audit admission webhook trust

```powershell
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get validatingwebhookconfigurations -o yaml
kubectl get mutatingwebhookconfigurations -o yaml
kubectl get services -A
```

**Expected:** identify webhook Service reference, CA bundle, timeout and failure policy. Check that the serving certificate SAN matches the actual service DNS name, that the configured CA trusts its chain, and that the webhook has Ready endpoints. Do not print or decode webhook TLS private keys.

**Failure distinctions:** `certificate signed by unknown authority` indicates trust mismatch; `certificate has expired or is not yet valid` indicates validity/clock issue; `certificate is valid for X, not Y` indicates SAN mismatch. Also investigate clock synchronization.

## 8. Lab 5 — Inventory application TLS and renewal ownership

```powershell
kubectl get ingress -A
kubectl get secrets -A --field-selector type=kubernetes.io/tls
kubectl get certificates -A
kubectl get gateway -A
```

**Expected:** inventory TLS Secret names, Ingress/Gateway references and cert-manager Certificates where installed. Missing Gateway/cert-manager APIs are expected in clusters without those extensions. Secret metadata can be inspected without revealing `tls.key`.

**Rotation plan:** confirm owner/issuer, SANs, trust chain, replacement Secret mechanism, controller reload behavior, monitoring, old/new CA overlap if needed, and rollback authority.

## 9. Lab 6 — Certificate expiry monitoring and alert design

| Severity | Illustrative threshold | Response |
|---|---|---|
| Warning | 30 days before expiry | Confirm owner and renewal automation |
| Elevated | 14 days | Investigate failed renewal and schedule change |
| Critical | 7 days | Escalate and validate recovery plan |
| Incident | Expired / active TLS errors | Restore service and trust safely |

Thresholds are examples, not universal SLOs. Monitor endpoint certificate expiry, cert-manager readiness/renewal errors, kubelet CSR Pending/Denied trends, webhook handshake errors, API admission failures, and synthetic TLS checks. Document issuer, renewal process, owner and alert destination for every certificate class.

## 10. Lab 7 — Webhook certificate rotation incident

**Scenario:** the webhook's serving certificate rotates to a new issuer, but the API server still trusts the old CA bundle. New Pods fail admission while existing Pods continue running.

```powershell
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get deployments -A
kubectl get pods -A --field-selector=status.phase=Pending
kubectl get events -A --sort-by=.lastTimestamp
kubectl get apiservices
```

**Required response:**
1. Freeze unrelated deployments and capture the exact API error.
2. Identify the webhook, backing Service, endpoints and controller.
3. Compare the serving certificate issuer, SAN and validity against the webhook caBundle.
4. Confirm whether the leaf renewal unexpectedly changed CA or a CA cutover was incomplete.
5. Repair the trust configuration using the webhook operator's supported reconciliation process.
6. Avoid disabling TLS verification or globally weakening the webhook failure policy.
7. Verify new Pods can be admitted, workloads become Ready and application SLIs recover.
8. Document owner, timeline, blast radius, alerting and prevention.

## 11. Platform-specific rotation responsibilities

### kubeadm / self-managed

Authorized control-plane administrators can use `kubeadm certs check-expiration` and version-specific kubeadm renewal procedures. Back up etcd and PKI securely before changes; coordinate HA control-plane component restarts. **Do not run `kubeadm certs renew all` as a generic incident fix.** External CAs and etcd certificates may require separate procedures.

### Amazon EKS

EKS manages the managed control plane's certificates. Teams remain responsible for webhook, ingress, application and add-on TLS. Use AWS-supported diagnostics; do not attempt direct access to managed control-plane PKI.

### Azure AKS

AKS manages major control-plane PKI lifecycles; cluster credential/certificate rotation follows AKS-specific documented workflows. Teams manage their own webhook and application TLS. Validate node-pool and identity impacts.

### Google GKE

GKE manages control-plane PKI, with provider-specific credential/CA rotation workflows. Application TLS and third-party webhook certificates remain separately owned. Do not apply kubeadm commands to managed control planes.

## 12. Troubleshooting matrix

| Symptom | Likely cause | Check |
|---|---|---|
| Expired certificate | Renewal failed | notAfter, issuer/controller logs |
| Not yet valid | Clock skew / issuance issue | notBefore, time sync |
| Unknown authority | Missing/wrong CA | Issuer and trust bundle |
| Hostname mismatch | Incorrect SAN | Endpoint versus SAN |
| Kubelet auth errors | Client cert/CSR issue | Kubelet logs, CSR signer |
| Webhook outage after Secret update | Trust or reload issue | caBundle, Service endpoints |
| API outage after CA rotation | Incomplete propagation | Component trust stores |
| Only some clients fail | Different trust stores | Client CA settings |
| cert-manager not renewing | Issuer or challenge failure | Certificate/Order/Challenge events |

## 13. Production rotation runbook

### Prepare

1. Identify certificate, issuer, SANs, expiry, owner and dependent clients.
2. Distinguish leaf renewal from CA rotation and enumerate all trust bundles.
3. Confirm backup/restore, staging rehearsal, maintenance approval and abort conditions.
4. Prepare overlapping trust for CA cutover when supported.
5. Baseline TLS errors, webhook admission latency and customer-facing SLIs.

### Execute

1. Capture current public certificate fingerprint and validity (never private keys).
2. Issue new certificate with correct SANs, EKU and chain.
3. Install via supported provider/operator or Secret rotation workflow.
4. Reconcile trust bundles and reload/restart serving processes as required.
5. Verify trusted TLS handshakes, API operations and new Pod admission.
6. Monitor errors, readiness and application traffic.

### Validate and close

1. Confirm new certificate is served and trusted by every relying party.
2. Confirm expected issuer, SANs and expiry.
3. Verify kubelet/API, webhook, ingress and workload flows as applicable.
4. Remove old CA trust only after safe migration and verification.
5. Update inventory, renewal automation, incident documentation and alert ownership.

**Abort:** stop if quorum-critical components lose connectivity, webhook failures rise, trust propagation is incomplete, or certificate SANs are wrong. CA rotation may require staged forward-fix rather than a simple rollback.

## 14. Acceptance checklist

- [ ] Certificate classes and owners inventoried.
- [ ] API endpoint and CA configuration inspected without credential exposure.
- [ ] Public certificate issuer, SAN and expiry inspected.
- [ ] CSR workflow reviewed without indiscriminate approval.
- [ ] Webhook serving certificate and caBundle trust reviewed.
- [ ] Application TLS inventory created without private keys.
- [ ] Expiry alerts and escalation ownership defined.
- [ ] Expiry, CA trust and SAN mismatch failures distinguished.
- [ ] Provider-managed and kubeadm responsibilities distinguished.
- [ ] Incident response and rotation runbooks documented.
- [ ] Actual runtime validation and independent technical review completed before marking Lab Validated.

**Status:** Draft — runtime validation and technical review pending.

## 15. References

- [Kubernetes PKI Certificates](https://kubernetes.io/docs/setup/best-practices/certificates/)
- [Certificate Signing Requests](https://kubernetes.io/docs/reference/access-authn-authz/certificate-signing-requests/)
- [Kubeadm Certificate Management](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-certs/)
- [Dynamic Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [cert-manager](https://cert-manager.io/docs/)

**Next:** Chapter 050 — Cluster Upgrade and Maintenance Project (Part 10 capstone).