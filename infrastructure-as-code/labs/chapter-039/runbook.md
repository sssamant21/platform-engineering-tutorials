# Chapter 039 — Production compute/EKS runbooks

## Deployment and promotion
1. Verify AWS STS principal, account, region, provider lock and backend state isolation.
2. Confirm approved AMI, IMDSv2, EBS encryption, ASG limits and instance profile.
3. Verify ALB HTTPS, listener/target health, health check and security groups.
4. Review EKS endpoint, cluster logs, node groups, add-ons, workload IAM and PDBs.
5. Run policy, unit tests, plan and destructive-action review; obtain SRE/DBRE approval.
6. Roll out canary; watch 5xx, p99, target health, pending pods, node readiness and DB connection pressure.
7. Record CI, change ticket, plan digest and SLO evidence; stop on rollback threshold.

## Failed ASG refresh
Pause refresh; inspect EC2 launch failures, AMI, instance profile, subnet IP and target health. Restore reviewed launch template version, verify healthy target count and capacity.

## EKS node incident
Freeze upgrades; inspect node conditions, CNI, kubelet, PDB and CSI. Drain only with approved disruption budget; maintain zonal capacity and verify application health.

## DB connection storm
Freeze application scale-up, throttle concurrency, inspect DB max connections and wait events, adjust pools/rate limits with DBRE review, confirm p99 recovery.

## IAM incident
Verify workload role and STS trust; avoid broadening node role to unblock pods. Contain credential exposure and audit CloudTrail.

## Disaster recovery
Independently validate Kubernetes manifests, volumes, database backup restoration, KMS decrypt and cross-AZ/region traffic. Terraform state restore does not recover application data.
