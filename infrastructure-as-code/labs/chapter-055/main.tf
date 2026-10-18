locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "terraform"
  }
}
resource "terraform_data" "foundation_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    cluster_context_verified = var.cluster_context_verified
    state_isolated = var.state_isolated
    cni_enforced = var.cni_enforced
    csi_ready = var.csi_ready
    observability_ready = var.observability_ready
    capacity_reviewed = var.capacity_reviewed
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.cluster_context_verified && var.state_isolated && var.cni_enforced && var.csi_ready && var.observability_ready && var.capacity_reviewed)
      error_message = "production foundation safeguards required"
    }
  }
}

resource "terraform_data" "security_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    dedicated_service_accounts = var.dedicated_service_accounts
    rbac_least_privilege = var.rbac_least_privilege
    psa_restricted = var.psa_restricted
    default_deny_network = var.default_deny_network
    dns_db_egress_scoped = var.dns_db_egress_scoped
    quotas_enforced = var.quotas_enforced
    secrets_excluded_from_state = var.secrets_excluded_from_state
    wildcard_cluster_admin = var.wildcard_cluster_admin
    dependency = terraform_data.foundation_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.dedicated_service_accounts && var.rbac_least_privilege && var.psa_restricted && var.default_deny_network && var.dns_db_egress_scoped && var.quotas_enforced && var.secrets_excluded_from_state && !var.wildcard_cluster_admin)
      error_message = "production security safeguards required"
    }
  }
}

resource "terraform_data" "delivery_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    provider_chart_pinned = var.provider_chart_pinned
    chart_provenance_reviewed = var.chart_provenance_reviewed
    crd_staged = var.crd_staged
    single_gitops_owner = var.single_gitops_owner
    rollout_tested = var.rollout_tested
    pdb_reviewed = var.pdb_reviewed
    rollback_tested = var.rollback_tested
    competing_reconciler = var.competing_reconciler
    dependency = terraform_data.security_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.provider_chart_pinned && var.chart_provenance_reviewed && var.crd_staged && var.single_gitops_owner && var.rollout_tested && var.pdb_reviewed && var.rollback_tested && !var.competing_reconciler)
      error_message = "production delivery safeguards required"
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
    backup_tested = var.backup_tested
    restore_tested = var.restore_tested
    rpo_rto_measured = var.rpo_rto_measured
    game_day_completed = var.game_day_completed
    audit_logs_enabled = var.audit_logs_enabled
    security_approved = var.security_approved
    dbre_approved = var.dbre_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    unapproved_pvc_delete = var.unapproved_pvc_delete
    dependency = terraform_data.delivery_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.backup_tested && var.restore_tested && var.rpo_rto_measured && var.game_day_completed && var.audit_logs_enabled && var.security_approved && var.dbre_approved && var.change_approved && !var.unapproved_destroy && !var.unapproved_pvc_delete)
      error_message = "production operations safeguards required"
    }
  }
}
