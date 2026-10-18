locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "terraform"
  }
}
resource "terraform_data" "workload_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    immutable_image = var.immutable_image
    readiness_probe = var.readiness_probe
    liveness_probe = var.liveness_probe
    startup_probe = var.startup_probe
    resource_requests = var.resource_requests
    pdb_reviewed = var.pdb_reviewed
    hpa_pool_capacity_reviewed = var.hpa_pool_capacity_reviewed
    graceful_shutdown = var.graceful_shutdown
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.immutable_image && var.readiness_probe && var.liveness_probe && var.startup_probe && var.resource_requests && var.pdb_reviewed && var.hpa_pool_capacity_reviewed && var.graceful_shutdown)
      error_message = "production workload safeguards required"
    }
  }
}

resource "terraform_data" "storage_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    stateful_operator_reviewed = var.stateful_operator_reviewed
    pvc_reclaim_reviewed = var.pvc_reclaim_reviewed
    csi_topology_reviewed = var.csi_topology_reviewed
    snapshot_policy_reviewed = var.snapshot_policy_reviewed
    backup_tested = var.backup_tested
    restore_tested = var.restore_tested
    rpo_rto_measured = var.rpo_rto_measured
    dependency = terraform_data.workload_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.stateful_operator_reviewed && var.pvc_reclaim_reviewed && var.csi_topology_reviewed && var.snapshot_policy_reviewed && var.backup_tested && var.restore_tested && var.rpo_rto_measured)
      error_message = "production storage safeguards required"
    }
  }
}

resource "terraform_data" "helm_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    provider_pinned = var.provider_pinned
    chart_version_pinned = var.chart_version_pinned
    image_digest_pinned = var.image_digest_pinned
    crd_staged = var.crd_staged
    chart_rbac_reviewed = var.chart_rbac_reviewed
    gitops_ownership_defined = var.gitops_ownership_defined
    secrets_excluded_from_state = var.secrets_excluded_from_state
    unapproved_uninstall = var.unapproved_uninstall
    dependency = terraform_data.storage_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.provider_pinned && var.chart_version_pinned && var.image_digest_pinned && var.crd_staged && var.chart_rbac_reviewed && var.gitops_ownership_defined && var.secrets_excluded_from_state && !var.unapproved_uninstall)
      error_message = "production helm safeguards required"
    }
  }
}

resource "terraform_data" "operations_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    audit_logs_enabled = var.audit_logs_enabled
    monitoring_enabled = var.monitoring_enabled
    rollback_tested = var.rollback_tested
    dr_runbook_tested = var.dr_runbook_tested
    security_approved = var.security_approved
    dbre_approved = var.dbre_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.helm_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.audit_logs_enabled && var.monitoring_enabled && var.rollback_tested && var.dr_runbook_tested && var.security_approved && var.dbre_approved && var.change_approved && !var.unapproved_destroy)
      error_message = "production operations safeguards required"
    }
  }
}
