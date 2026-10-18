locals {
  labels = {
    environment = var.environment
    owner = var.owner
    managed-by = "opentofu-terragrunt"
  }
}
resource "terraform_data" "migration_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    tofu_version_pinned = var.tofu_version_pinned
    terraform_baseline_recorded = var.terraform_baseline_recorded
    provider_versions_pinned = var.provider_versions_pinned
    module_revisions_pinned = var.module_revisions_pinned
    schema_compatibility_reviewed = var.schema_compatibility_reviewed
    migration_rehearsed = var.migration_rehearsed
    rollback_documented = var.rollback_documented
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.tofu_version_pinned && var.terraform_baseline_recorded && var.provider_versions_pinned && var.module_revisions_pinned && var.schema_compatibility_reviewed && var.migration_rehearsed && var.rollback_documented)
      error_message = "production migration capstone safeguards required"
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
    lineage_serial_recorded = var.lineage_serial_recorded
    state_backup_verified = var.state_backup_verified
    isolated_restore_tested = var.isolated_restore_tested
    exclusive_writer = var.exclusive_writer
    concurrent_writers = var.concurrent_writers
    dependency = terraform_data.migration_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.backend_keys_unique && var.backend_encrypted && var.backend_lock_verified && var.lineage_serial_recorded && var.state_backup_verified && var.isolated_restore_tested && var.exclusive_writer && !var.concurrent_writers)
      error_message = "production state capstone safeguards required"
    }
  }
}

resource "terraform_data" "graph_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    dag_acyclic = var.dag_acyclic
    dependency_outputs_reviewed = var.dependency_outputs_reviewed
    prod_mock_outputs_disabled = var.prod_mock_outputs_disabled
    bounded_parallelism = var.bounded_parallelism
    partial_failure_runbook = var.partial_failure_runbook
    gitops_single_writer = var.gitops_single_writer
    competing_orchestrators = var.competing_orchestrators
    dependency = terraform_data.state_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.dag_acyclic && var.dependency_outputs_reviewed && var.prod_mock_outputs_disabled && var.bounded_parallelism && var.partial_failure_runbook && var.gitops_single_writer && !var.competing_orchestrators)
      error_message = "production graph capstone safeguards required"
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
    native_plan_adapter_reviewed = var.native_plan_adapter_reviewed
    plan_policy_enabled = var.plan_policy_enabled
    immutable_artifacts = var.immutable_artifacts
    environment_approvals = var.environment_approvals
    untrusted_pr_prod_access = var.untrusted_pr_prod_access
    dependency = terraform_data.graph_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.oidc_short_lived && var.native_plan_adapter_reviewed && var.plan_policy_enabled && var.immutable_artifacts && var.environment_approvals && !var.untrusted_pr_prod_access)
      error_message = "production delivery capstone safeguards required"
    }
  }
}

resource "terraform_data" "recovery_contract" {
  input = {
    root_name = var.root_name
    backend_key = var.backend_key
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_approved = var.change_approved
    pitr_verified = var.pitr_verified
    rpo_rto_measured = var.rpo_rto_measured
    slo_monitored = var.slo_monitored
    incident_game_day = var.incident_game_day
    unapproved_destroy = var.unapproved_destroy
    dependency = terraform_data.delivery_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.dbre_approved && var.security_approved && var.change_approved && var.pitr_verified && var.rpo_rto_measured && var.slo_monitored && var.incident_game_day && !var.unapproved_destroy)
      error_message = "production recovery capstone safeguards required"
    }
  }
}
