locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "terragrunt"
  }
}
resource "terraform_data" "composition_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    terragrunt_version_pinned = var.terragrunt_version_pinned
    tofu_version_pinned = var.tofu_version_pinned
    include_paths_reviewed = var.include_paths_reviewed
    parent_local_scope_reviewed = var.parent_local_scope_reviewed
    environment_inputs_explicit = var.environment_inputs_explicit
    module_source_pinned = var.module_source_pinned
    effective_config_reviewed = var.effective_config_reviewed
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.terragrunt_version_pinned && var.tofu_version_pinned && var.include_paths_reviewed && var.parent_local_scope_reviewed && var.environment_inputs_explicit && var.module_source_pinned && var.effective_config_reviewed)
      error_message = "production composition orchestration safeguards required"
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
    backend_keys_unique = var.backend_keys_unique
    backend_encrypted = var.backend_encrypted
    backend_lock_verified = var.backend_lock_verified
    state_backup_verified = var.state_backup_verified
    restore_tested = var.restore_tested
    account_region_isolated = var.account_region_isolated
    concurrent_writers = var.concurrent_writers
    dependency = terraform_data.composition_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.backend_keys_unique && var.backend_encrypted && var.backend_lock_verified && var.state_backup_verified && var.restore_tested && var.account_region_isolated && !var.concurrent_writers)
      error_message = "production state orchestration safeguards required"
    }
  }
}

resource "terraform_data" "dependency_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    graph_acyclic = var.graph_acyclic
    dependency_outputs_reviewed = var.dependency_outputs_reviewed
    mock_outputs_disabled_prod = var.mock_outputs_disabled_prod
    bounded_parallelism = var.bounded_parallelism
    partial_failure_runbook = var.partial_failure_runbook
    promotions_approved = var.promotions_approved
    competing_orchestrators = var.competing_orchestrators
    dependency = terraform_data.state_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.graph_acyclic && var.dependency_outputs_reviewed && var.mock_outputs_disabled_prod && var.bounded_parallelism && var.partial_failure_runbook && var.promotions_approved && !var.competing_orchestrators)
      error_message = "production dependency orchestration safeguards required"
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
    oidc_short_lived = var.oidc_short_lived
    policy_gate_enabled = var.policy_gate_enabled
    drift_reviewed = var.drift_reviewed
    slo_monitored = var.slo_monitored
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.dependency_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.oidc_short_lived && var.policy_gate_enabled && var.drift_reviewed && var.slo_monitored && var.dbre_approved && var.security_approved && var.change_approved && !var.unapproved_destroy)
      error_message = "production operations orchestration safeguards required"
    }
  }
}
