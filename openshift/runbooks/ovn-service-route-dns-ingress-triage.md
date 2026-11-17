# Runbook — OVN, Service, Route, DNS and Ingress Triage

**Trigger:** HTTP 503/timeout, Service unreachable, DNS failure, degraded network/dns/ingress Operator.  
**Scope:** Read-only first response on OCP 4.x. **Status:** Draft; not runtime validated.  
**Ownership:** Application team owns workload readiness and Service/Route configuration; Platform/SRE owns cluster networking, Operators and ingress; infrastructure/network team owns external DNS, LB and firewalls. Ownership may vary by organization.

## 1. Declare impact and verify target

Record incident start, affected applications, user regions, recent deploy/upgrade/change, and on-call owners.

```bash
oc whoami
oc config current-context
oc whoami --show-server
oc get clusterversion
```

Stop if cluster identity is uncertain. Do not print tokens or kubeconfig credentials.

## 2. Follow the request path

```bash
oc get routes.route.openshift.io -n <project>
oc describe route <route-name> -n <project>
oc describe service <service-name> -n <project>
oc get endpointslices.discovery.k8s.io -n <project> -l kubernetes.io/service-name=<service-name> -o wide
oc get pods -n <project> -o wide --show-labels
oc get networkpolicies.networking.k8s.io -n <project>
oc get events -n <project> --sort-by=.lastTimestamp
```

If Route is not used, begin with the Service and relevant client protocol. Compare the Service selector and targetPort with pod labels and readiness; inspect EndpointSlice ready conditions. Do not treat empty endpoints as proof of a networking plugin fault.

## 3. Inspect platform conditions (cluster-wide RBAC required)

```bash
oc get clusteroperator network dns ingress
oc describe clusteroperator network
oc describe clusteroperator dns
oc describe clusteroperator ingress
oc get network.config.openshift.io cluster
oc get pods -n openshift-ovn-kubernetes
oc get pods -n openshift-dns
oc get pods -n openshift-ingress
```

Interpret Available/Progressing/Degraded in the context of upgrades. For external DNS, compare the approved hostname against Route admission and the expected ingress endpoint; network-team DNS checks may be necessary. Use operator logs only with appropriate access and sanitize them.

## 4. Decision and escalation

| Evidence | Primary escalation |
| --- | --- |
| Service selector mismatch, unready pods, bad targetPort | Application/deployment owner |
| Route admission or ingress router degradation | Platform/SRE Ingress owner |
| DNS Operator unhealthy, internal DNS issue | Platform/SRE DNS owner |
| Network Operator/OVN unhealthy or policy issue | Platform/SRE network owner |
| External DNS/LB/firewall path failure | Infrastructure/network owner |
| Stateful application protocol/connectivity issue | Application + DBRE + platform jointly |

Collect exact time, sanitized context, object names, observed conditions, correlation to change, client error class and evidence. Avoid disclosing secrets, internal topology unnecessarily or private Route TLS keys.

## 5. Change and rollback gate

This runbook **authorizes no mutations**. Do not restart OVN/router pods, edit cluster Network/DNS/IngressController configuration, remove NetworkPolicies, change Route TLS, drain nodes, or bypass security controls as an unreviewed mitigation. Before a separate approved fix, establish blast radius, maintenance/change owner, workload/DB impact, rollback feasibility, monitoring, success criteria and stop conditions. Cluster-wide networking edits can be disruptive and may not support simple rollback; follow Red Hat version-specific support procedures.

## 6. Closeout

Confirm service-level recovery with application owner, capture before/after observations, document root cause and change reference, and schedule follow-up preventive actions.

## Official documentation

- [OCP 4.22 OVN-Kubernetes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/ovn-kubernetes_network_plugin/index)
- [OCP 4.22 Networking Operators](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/networking_operators/)
- [OCP 4.22 Networking overview](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/networking_overview/index)
