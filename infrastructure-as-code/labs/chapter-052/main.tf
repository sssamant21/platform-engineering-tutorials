locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "terraform"
  }
}
resource "terraform_data" "namespace_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    namespace_owner_verified = var.namespace_owner_verified
    quota_enabled = var.quota_enabled
    limitrange_enabled = var.limitrange_enabled
    psa_restricted = var.psa_restricted
    namespace_deletion_protected = var.namespace_deletion_protected
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.namespace_owner_verified && var.quota_enabled && var.limitrange_enabled && var.psa_restricted && var.namespace_deletion_protected)
      error_message = "production namespace safeguards required"
    }
  }
}

resource "terraform_data" "rbac_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    dedicated_service_accounts = var.dedicated_service_accounts
    rbac_least_privilege = var.rbac_least_privilege
    rbac_scoped_rolebindings = var.rbac_scoped_rolebindings
    effective_permissions_tested = var.effective_permissions_tested
    token_automount_disabled = var.token_automount_disabled
    wildcard_cluster_admin = var.wildcard_cluster_admin
    default_service_account_used = var.default_service_account_used
    dependency = terraform_data.namespace_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.dedicated_service_accounts && var.rbac_least_privilege && var.rbac_scoped_rolebindings && var.effective_permissions_tested && var.token_automount_disabled && !var.wildcard_cluster_admin && !var.default_service_account_used)
      error_message = "production rbac safeguards required"
    }
  }
}

resource "terraform_data" "network_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    default_deny_ingress = var.default_deny_ingress
    default_deny_egress = var.default_deny_egress
    dns_egress_explicit = var.dns_egress_explicit
    database_egress_scoped = var.database_egress_scoped
    cni_enforcement_tested = var.cni_enforcement_tested
    broad_egress = var.broad_egress
    dependency = terraform_data.rbac_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.default_deny_ingress && var.default_deny_egress && var.dns_egress_explicit && var.database_egress_scoped && var.cni_enforcement_tested && !var.broad_egress)
      error_message = "production network safeguards required"
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
    tenant_cost_labels = var.tenant_cost_labels
    backup_reviewed = var.backup_reviewed
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.network_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.audit_logs_enabled && var.monitoring_enabled && var.tenant_cost_labels && var.backup_reviewed && var.dbre_approved && var.security_approved && var.change_approved && !var.unapproved_destroy)
      error_message = "production operations safeguards required"
    }
  }
}
