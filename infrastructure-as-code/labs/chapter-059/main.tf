locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "terragrunt"
  }
}
resource "terraform_data" "graph_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    graph_acyclic = var.graph_acyclic
    output_contracts_reviewed = var.output_contracts_reviewed
    upstream_state_verified = var.upstream_state_verified
    mock_outputs_disabled_prod = var.mock_outputs_disabled_prod
    failure_domains_separated = var.failure_domains_separated
    bounded_parallelism = var.bounded_parallelism
    graph_reviewed = var.graph_reviewed
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.graph_acyclic && var.output_contracts_reviewed && var.upstream_state_verified && var.mock_outputs_disabled_prod && var.failure_domains_separated && var.bounded_parallelism && var.graph_reviewed)
      error_message = "production graph orchestration safeguards required"
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
    dependency = terraform_data.graph_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.backend_keys_unique && var.backend_encrypted && var.backend_lock_verified && var.state_backup_verified && var.restore_tested && var.account_region_isolated && !var.concurrent_writers)
      error_message = "production state orchestration safeguards required"
    }
  }
}

resource "terraform_data" "cicd_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    toolchain_pinned = var.toolchain_pinned
    module_revisions_pinned = var.module_revisions_pinned
    oidc_short_lived = var.oidc_short_lived
    plan_artifact_reviewed = var.plan_artifact_reviewed
    native_plan_adapter_reviewed = var.native_plan_adapter_reviewed
    environment_approval_required = var.environment_approval_required
    untrusted_pr_prod_access = var.untrusted_pr_prod_access
    dependency = terraform_data.state_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.toolchain_pinned && var.module_revisions_pinned && var.oidc_short_lived && var.plan_artifact_reviewed && var.native_plan_adapter_reviewed && var.environment_approval_required && !var.untrusted_pr_prod_access)
      error_message = "production cicd orchestration safeguards required"
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
    policy_gate_enabled = var.policy_gate_enabled
    drift_reviewed = var.drift_reviewed
    slo_monitored = var.slo_monitored
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_approved = var.change_approved
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.cicd_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.policy_gate_enabled && var.drift_reviewed && var.slo_monitored && var.dbre_approved && var.security_approved && var.change_approved && !var.unapproved_destroy)
      error_message = "production operations orchestration safeguards required"
    }
  }
}
