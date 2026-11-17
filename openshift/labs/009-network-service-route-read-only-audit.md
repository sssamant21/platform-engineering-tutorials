# Lab 009 — Read-only Service, Route and DNS Audit

**Duration:** 30–40 minutes within Chapter 009. **Status:** Not executed.  
**Access:** Authorized OCP 4.x cluster; read-only project permissions; optional cluster-wide Operator read access.  
**Safety:** No `oc create`, `oc patch`, `oc edit`, `oc delete`, `oc debug`, or `oc exec` in this lab.

## Setup and identity gate

```bash
oc whoami
oc config current-context
oc whoami --show-server
oc version
oc auth can-i list services -n <project>
oc auth can-i list routes.route.openshift.io -n <project>
oc auth can-i list endpointslices.discovery.k8s.io -n <project>
```

If any permission is denied, record it and omit that step; do not elevate privileges.

## Procedure

1. Obtain an **approved project** and one Service name from the application owner. If no Route exists, record 'not applicable' rather than creating one.
2. Inspect Service and backends:
   ```bash
   oc get service <service-name> -n <project> -o yaml
   oc get endpointslices.discovery.k8s.io -n <project> -l kubernetes.io/service-name=<service-name> -o wide
   oc get pods -n <project> -o wide --show-labels
   ```
3. Inspect route admission and TLS metadata only, if applicable:
   ```bash
   oc describe route <route-name> -n <project>
   ```
   **Do not copy full Route YAML into public evidence:** it can contain sensitive TLS material.
4. Inspect policies and events:
   ```bash
   oc get networkpolicies.networking.k8s.io -n <project>
   oc get events -n <project> --sort-by=.lastTimestamp
   ```
5. If explicitly authorized for cluster-scoped resources:
   ```bash
   oc get clusteroperator network dns ingress
   oc get network.config.openshift.io cluster
   oc get ingresscontrollers.operator.openshift.io -n openshift-ingress-operator
   ```
6. For an approved public hostname, inspect DNS using `dig <hostname>` (Linux) or `Resolve-DnsName <hostname>` (PowerShell). Do not perform active traffic tests unless approved.

## Expected interpretation

- Service selector labels match the intended pods, unless the Service is deliberately selectorless.
- EndpointSlices have expected endpoint addresses and ready conditions for available workloads.
- A Route, when used, points to the expected Service and has appropriate admission conditions.
- Network, DNS and Ingress Operators are assessed in the context of maintenance/upgrade activity.
- Any failure is attributed to a layer only when evidence supports that conclusion.

## Evidence template

| Item | Actual evidence |
| --- | --- |
| UTC timestamp and sanitized cluster | Not executed |
| OCP version and user context verified | Not executed |
| Project and Service | Not executed |
| Service selector and targetPort | Not executed |
| EndpointSlice readiness | Not executed |
| Route admission/TLS metadata, if applicable | Not executed |
| NetworkPolicies and events | Not executed |
| Network/DNS/Ingress Operator conditions, if authorized | Not executed |
| DNS observations, if authorized | Not executed |
| Root-cause hypothesis / escalation owner | Not executed |
| Independent reviewer | Pending |

**Pass gate:** Read-only audit evidence, clear differentiation of backend vs DNS vs ingress vs OVN hypotheses, and no secrets. **Current result: NOT RUN.**

[Return to Chapter 009](../chapters/009-ovn-kubernetes-services-routes-and-ingress.md)
