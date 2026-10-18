locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "terraform"
  }
}
resource "terraform_data" "supply_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    provider_pinned = var.provider_pinned
    chart_version_pinned = var.chart_version_pinned
    repository_verified = var.repository_verified
    image_digest_pinned = var.image_digest_pinned
    chart_render_reviewed = var.chart_render_reviewed
    chart_rbac_reviewed = var.chart_rbac_reviewed
    chart_hooks_reviewed = var.chart_hooks_reviewed
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.provider_pinned && var.chart_version_pinned && var.repository_verified && var.image_digest_pinned && var.chart_render_reviewed && var.chart_rbac_reviewed && var.chart_hooks_reviewed)
      error_message = "production supply safeguards required"
    }
  }
}

resource "terraform_data" "release_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    crd_staged = var.crd_staged
    rollout_health_checked = var.rollout_health_checked
    rollback_tested = var.rollback_tested
    pdb_reviewed = var.pdb_reviewed
    secrets_excluded_from_state = var.secrets_excluded_from_state
    unapproved_uninstall = var.unapproved_uninstall
    unapproved_crd_delete = var.unapproved_crd_delete
    dependency = terraform_data.supply_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.crd_staged && var.rollout_health_checked && var.rollback_tested && var.pdb_reviewed && var.secrets_excluded_from_state && !var.unapproved_uninstall && !var.unapproved_crd_delete)
      error_message = "production release safeguards required"
    }
  }
}

resource "terraform_data" "gitops_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    owner_registry = var.owner_registry
    single_reconciler = var.single_reconciler
    drift_reviewed = var.drift_reviewed
    handoff_documented = var.handoff_documented
    policy_gate_enabled = var.policy_gate_enabled
    competing_reconciler = var.competing_reconciler
    dependency = terraform_data.release_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.owner_registry && var.single_reconciler && var.drift_reviewed && var.handoff_documented && var.policy_gate_enabled && !var.competing_reconciler)
      error_message = "production gitops safeguards required"
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
    backup_tested = var.backup_tested
    rpo_rto_measured = var.rpo_rto_measured
    security_approved = var.security_approved
    dbre_approved = var.dbre_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.gitops_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.audit_logs_enabled && var.monitoring_enabled && var.backup_tested && var.rpo_rto_measured && var.security_approved && var.dbre_approved && var.change_approved && !var.unapproved_destroy)
      error_message = "production operations safeguards required"
    }
  }
}
