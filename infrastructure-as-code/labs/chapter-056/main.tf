locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "opentofu"
  }
}
resource "terraform_data" "compatibility_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    tofu_version_pinned = var.tofu_version_pinned
    terraform_version_inventoried = var.terraform_version_inventoried
    provider_versions_pinned = var.provider_versions_pinned
    module_sources_reviewed = var.module_sources_reviewed
    state_format_reviewed = var.state_format_reviewed
    backend_compatibility_reviewed = var.backend_compatibility_reviewed
    plan_parity_reviewed = var.plan_parity_reviewed
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.tofu_version_pinned && var.terraform_version_inventoried && var.provider_versions_pinned && var.module_sources_reviewed && var.state_format_reviewed && var.backend_compatibility_reviewed && var.plan_parity_reviewed)
      error_message = "production compatibility migration safeguards required"
    }
  }
}

resource "terraform_data" "state_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    state_backup_verified = var.state_backup_verified
    restore_tested = var.restore_tested
    exclusive_writer = var.exclusive_writer
    lock_owner_verified = var.lock_owner_verified
    lineage_serial_recorded = var.lineage_serial_recorded
    backend_encrypted = var.backend_encrypted
    rollback_documented = var.rollback_documented
    concurrent_writers = var.concurrent_writers
    dependency = terraform_data.compatibility_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.state_backup_verified && var.restore_tested && var.exclusive_writer && var.lock_owner_verified && var.lineage_serial_recorded && var.backend_encrypted && var.rollback_documented && !var.concurrent_writers)
      error_message = "production state migration safeguards required"
    }
  }
}

resource "terraform_data" "delivery_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    oidc_short_lived = var.oidc_short_lived
    ci_executor_pinned = var.ci_executor_pinned
    policy_gate_enabled = var.policy_gate_enabled
    drift_reviewed = var.drift_reviewed
    secret_state_prohibited = var.secret_state_prohibited
    environment_isolated = var.environment_isolated
    destructive_plan_approved = var.destructive_plan_approved
    dependency = terraform_data.state_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.oidc_short_lived && var.ci_executor_pinned && var.policy_gate_enabled && var.drift_reviewed && var.secret_state_prohibited && var.environment_isolated && var.destructive_plan_approved)
      error_message = "production delivery migration safeguards required"
    }
  }
}

resource "terraform_data" "operations_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_approved = var.change_approved
    slo_baseline_recorded = var.slo_baseline_recorded
    incident_drill_completed = var.incident_drill_completed
    monitoring_enabled = var.monitoring_enabled
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.delivery_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.dbre_approved && var.security_approved && var.change_approved && var.slo_baseline_recorded && var.incident_drill_completed && var.monitoring_enabled && !var.unapproved_destroy)
      error_message = "production operations migration safeguards required"
    }
  }
}
