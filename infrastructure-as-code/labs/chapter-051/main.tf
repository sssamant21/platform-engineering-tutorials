locals { labels = { environment = var.environment, owner = var.owner, managed-by = "terraform" } }
resource "terraform_data" "cluster_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    context_verified = var.context_verified
    api_healthy = var.api_healthy
    provider_pinned = var.provider_pinned
    state_isolated = var.state_isolated
    short_lived_identity = var.short_lived_identity
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.context_verified && var.api_healthy && var.provider_pinned && var.state_isolated && var.short_lived_identity)
      error_message = "production cluster_contract safeguards required"
    }
  }
}

resource "terraform_data" "tenant_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    namespace_isolated = var.namespace_isolated
    rbac_least_privilege = var.rbac_least_privilege
    network_default_deny = var.network_default_deny
    dns_egress_reviewed = var.dns_egress_reviewed
    quota_enabled = var.quota_enabled
    pod_security_enforced = var.pod_security_enforced
    wildcard_cluster_admin = var.wildcard_cluster_admin
    default_service_account_used = var.default_service_account_used
    dependency = terraform_data.cluster_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.namespace_isolated && var.rbac_least_privilege && var.network_default_deny && var.dns_egress_reviewed && var.quota_enabled && var.pod_security_enforced && !var.wildcard_cluster_admin && !var.default_service_account_used)
      error_message = "production tenant_contract safeguards required"
    }
  }
}

resource "terraform_data" "workload_contract" {
  input = {
    cluster_name = var.cluster_name
    namespace = var.namespace
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    image_digest_pinned = var.image_digest_pinned
    readiness_probe = var.readiness_probe
    pdb_reviewed = var.pdb_reviewed
    resource_requests = var.resource_requests
    db_connection_pool_reviewed = var.db_connection_pool_reviewed
    stateful_backup_tested = var.stateful_backup_tested
    secret_payload_in_state = var.secret_payload_in_state
    dependency = terraform_data.tenant_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.image_digest_pinned && var.readiness_probe && var.pdb_reviewed && var.resource_requests && var.db_connection_pool_reviewed && var.stateful_backup_tested && !var.secret_payload_in_state)
      error_message = "production workload_contract safeguards required"
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
    monitoring_enabled = var.monitoring_enabled
    audit_logs_enabled = var.audit_logs_enabled
    dr_runbook_tested = var.dr_runbook_tested
    security_approved = var.security_approved
    dbre_approved = var.dbre_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.workload_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.monitoring_enabled && var.audit_logs_enabled && var.dr_runbook_tested && var.security_approved && var.dbre_approved && var.change_approved && !var.unapproved_destroy)
      error_message = "production operations_contract safeguards required"
    }
  }
}
