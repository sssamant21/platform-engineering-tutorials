# Chapter 009 — OVN-Kubernetes, Services, Routes, DNS and Ingress

**Track:** Platform Engineering > OpenShift Administration  
**Duration:** ~60 minutes | **Baseline:** Red Hat OCP 4.22 | **Status:** Draft; runtime not executed  
**Prerequisites:** Chapters 001–008, an authorized `oc` login, and read permissions for the chosen project. Cluster-wide inventory requires additional RBAC. No changes are required.

## Outcomes

Explain the OpenShift network request path; distinguish OVN-Kubernetes, Service/EndpointSlice, DNS, Route and Ingress Controller failures; collect evidence without altering cluster networking; identify when application, platform or network teams own remediation.

## 1. Architecture and traffic flow

For an externally exposed HTTP application, the common path is:

```text
Client -> external DNS -> load balancer / ingress VIP
       -> OpenShift router (Ingress Controller)
       -> Route -> Service -> EndpointSlice -> ready application pod
```

For in-cluster traffic, pods typically resolve a Service name using cluster DNS and reach a Service VIP or endpoints through the configured network implementation. A **Route** is an OpenShift API object for exposing supported HTTP(S)/TLS applications; it is not a general-purpose TCP load balancer. An **IngressController** is managed by the OpenShift Ingress Operator and runs router workloads. OVN-Kubernetes provides the cluster pod/service network and policy enforcement, using OVN/OVS; it does not itself own external DNS records or the external load balancer.

Before assuming OVN-Kubernetes is in use, inspect the configured provider. OpenShift 4.22 defaults to OVN-Kubernetes, but actual cluster configuration is authoritative. The Cluster Network Operator reconciles networking; its status and network configuration must be interpreted separately from the DNS and Ingress Operators.

## 2. Confirm cluster and authorization

```bash
oc whoami
oc config current-context
oc whoami --show-server
oc version
oc auth can-i get services -n <project>
oc auth can-i list endpointslices.discovery.k8s.io -n <project>
oc auth can-i list routes.route.openshift.io -n <project>
oc auth can-i get clusteroperators
```

Use a project approved for inspection; do not substitute a production namespace without authorization. An RBAC denial is a finding, not permission to grant yourself elevated rights.

## 3. Cluster networking and Operator health (if authorized)

```bash
oc get network.config.openshift.io cluster -o yaml
oc get clusteroperator network dns ingress
oc describe clusteroperator network
oc get ingresscontrollers.operator.openshift.io -n openshift-ingress-operator
oc get pods -n openshift-ovn-kubernetes
oc get pods -n openshift-dns
oc get pods -n openshift-ingress
```

Check `spec.networkType` and status in the Network configuration, then inspect the relevant Operator conditions. Some cluster-scoped and platform namespaces are not visible to project-only readers. Do not infer a network outage solely from an inability to list resources.

## 4. Follow a Service and Route through to a workload

```bash
oc get services -n <project>
oc describe service <service-name> -n <project>
oc get endpointslices.discovery.k8s.io -n <project> -l kubernetes.io/service-name=<service-name> -o wide
oc get pods -n <project> -o wide --show-labels
oc get routes.route.openshift.io -n <project>
oc describe route <route-name> -n <project>
oc get networkpolicies.networking.k8s.io -n <project>
oc get events -n <project> --sort-by=.lastTimestamp
```

Correlate the Service selector to pod labels; check readiness, targetPort, EndpointSlice addresses and ready conditions. EndpointSlices are the primary modern discovery resource; do not depend on legacy Endpoints alone. For a selectorless Service, endpoints may be managed separately and the selector check is not applicable.

A Route may be admitted but still fail due to unhealthy backend endpoints, TLS configuration, ingress router availability, external DNS or load balancer problems. Inspect `status.ingress` and conditions, not just the existence of a Route.

## 5. Failure patterns and evidence

| Symptom | Possible layer | Read-only evidence |
| --- | --- | --- |
| DNS name does not resolve externally | External DNS or route host record | Approved DNS lookup from a trusted client; Route host and ingress domain |
| Internal Service name fails | Cluster DNS, search path or NetworkPolicy | DNS Operator, DNS pods, approved application logs |
| Service has no ready backends | Selector, readiness or pod scheduling | Service, EndpointSlice and matching pods |
| Route returns 503 | Router cannot reach a healthy backend, route/service mismatch or policy | Route conditions, endpoints, router health and application logs |
| Connection times out | LB/firewall, network policy, OVN path, node issue | Operator conditions, policies, event timeline and approved network telemetry |
| TLS failure | Route termination, certificate, SNI or client trust | Route TLS configuration (do not disclose private keys), certificate metadata, client error |

A 503 is not proof of an OVN failure. A DNS resolution problem is not necessarily a CoreDNS/OpenShift DNS problem; determine whether the failing lookup is external or internal first.

## 6. Windows PowerShell and Linux examples

All `oc` commands above work in either a compatible Linux shell or PowerShell with `oc` on PATH. For external DNS verification use `Resolve-DnsName <approved-hostname>` in PowerShell or `dig <approved-hostname>` on Linux where available. Do not run unapproved active network probes against production applications.

## 7. Incident exercise (read-only)

A production application reports intermittent HTTP 503 responses. First verify cluster context and business impact; capture the Route host/admission, Service selector, EndpointSlices, ready pod count, recent rollout, ingress Operator status and events. Classify whether evidence points to a backend deployment, platform ingress, or external networking. Recommend no changes until ownership and rollback gates are agreed.

For databases and Kafka, Routes are generally not the standard mechanism for native database protocols. Evaluate supported internal Services, network policies, client connection behavior and platform-specific exposure instead.

## 8. Acceptance and safety

Complete [Lab 009](../labs/009-network-service-route-read-only-audit.md). Use the [Network/Route triage runbook](../runbooks/ovn-service-route-dns-ingress-triage.md) for incidents. Record sanitized cluster/version, exact commands, permissions, observations and escalation. **Drafting is not live validation.** Any edit to Network/IngressController/DNS, Route TLS, NetworkPolicy, firewall, load balancer or node configuration requires impact assessment, approved change window, staged test and explicit rollback or recovery plan.

## References

- [Red Hat OCP 4.22 — OVN-Kubernetes network plugin](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/ovn-kubernetes_network_plugin/index)
- [Red Hat OCP 4.22 — Networking Operators](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/networking_operators/)
- [Red Hat OCP 4.22 — Networking overview](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/networking_overview/index)
- [Kubernetes networking fundamentals](../../../kubernetes/README.md)
