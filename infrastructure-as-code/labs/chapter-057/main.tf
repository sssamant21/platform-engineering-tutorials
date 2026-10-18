locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "opentofu"
  }
}
resource "terraform_data" "state_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    backend_isolated = var.backend_isolated
    backend_encrypted = var.backend_encrypted
    locking_verified = var.locking_verified
    lineage_recorded = var.lineage_recorded
    serial_recorded = var.serial_recorded
    state_backup_verified = var.state_backup_verified
    restore_tested = var.restore_tested
    exclusive_writer = var.exclusive_writer
    concurrent_writers = var.concurrent_writers
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.backend_isolated && var.backend_encrypted && var.locking_verified && var.lineage_recorded && var.serial_recorded && var.state_backup_verified && var.restore_tested && var.exclusive_writer && !var.concurrent_writers)
      error_message = "production state compatibility safeguards required"
    }
  }
}

resource "terraform_data" "provider_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    provider_source_pinned = var.provider_source_pinned
    provider_version_pinned = var.provider_version_pinned
    lockfile_reviewed = var.lockfile_reviewed
    schema_compatibility_reviewed = var.schema_compatibility_reviewed
    registry_trusted = var.registry_trusted
    auth_short_lived = var.auth_short_lived
    unexpected_replacement = var.unexpected_replacement
    dependency = terraform_data.state_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.provider_source_pinned && var.provider_version_pinned && var.lockfile_reviewed && var.schema_compatibility_reviewed && var.registry_trusted && var.auth_short_lived && !var.unexpected_replacement)
      error_message = "production provider compatibility safeguards required"
    }
  }
}

resource "terraform_data" "module_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    module_sources_pinned = var.module_sources_pinned
    module_contract_tested = var.module_contract_tested
    input_output_reviewed = var.input_output_reviewed
    address_migrations_reviewed = var.address_migrations_reviewed
    transitive_deps_reviewed = var.transitive_deps_reviewed
    module_rollback_tested = var.module_rollback_tested
    dependency = terraform_data.provider_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.module_sources_pinned && var.module_contract_tested && var.input_output_reviewed && var.address_migrations_reviewed && var.transitive_deps_reviewed && var.module_rollback_tested)
      error_message = "production module compatibility safeguards required"
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
    plan_policy_enabled = var.plan_policy_enabled
    native_plan_adapter_reviewed = var.native_plan_adapter_reviewed
    drift_reviewed = var.drift_reviewed
    slo_monitored = var.slo_monitored
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.module_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.plan_policy_enabled && var.native_plan_adapter_reviewed && var.drift_reviewed && var.slo_monitored && var.dbre_approved && var.security_approved && var.change_approved && !var.unapproved_destroy)
      error_message = "production operations compatibility safeguards required"
    }
  }
}
