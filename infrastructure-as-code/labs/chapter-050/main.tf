locals { labels = { environment = var.environment, owner = var.owner, managed-by = "terraform" } }
resource "terraform_data" "database_contract" {
  input = {
    project_id = var.project_id
    region = var.region
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    db_ha = var.db_ha
    db_pitr = var.db_pitr
    db_backup_enabled = var.db_backup_enabled
    db_restore_tested = var.db_restore_tested
    db_private_connectivity = var.db_private_connectivity
    db_public_ingress = var.db_public_ingress
    db_connection_pool_reviewed = var.db_connection_pool_reviewed
    db_replication_reviewed = var.db_replication_reviewed
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.db_ha && var.db_pitr && var.db_backup_enabled && var.db_restore_tested && var.db_private_connectivity && !var.db_public_ingress && var.db_connection_pool_reviewed && var.db_replication_reviewed)
      error_message = "production database_contract safeguards required"
    }
  }
}

resource "terraform_data" "storage_contract" {
  input = {
    project_id = var.project_id
    region = var.region
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    storage_public_access_prevention = var.storage_public_access_prevention
    storage_uniform_access = var.storage_uniform_access
    storage_versioning = var.storage_versioning
    storage_retention_reviewed = var.storage_retention_reviewed
    storage_lifecycle_reviewed = var.storage_lifecycle_reviewed
    storage_encrypted = var.storage_encrypted
    storage_recovery_tested = var.storage_recovery_tested
    dependency = terraform_data.database_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.storage_public_access_prevention && var.storage_uniform_access && var.storage_versioning && var.storage_retention_reviewed && var.storage_lifecycle_reviewed && var.storage_encrypted && var.storage_recovery_tested)
      error_message = "production storage_contract safeguards required"
    }
  }
}

resource "terraform_data" "security_contract" {
  input = {
    project_id = var.project_id
    region = var.region
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    kms_enabled = var.kms_enabled
    kms_recovery_tested = var.kms_recovery_tested
    kms_service_agent_reviewed = var.kms_service_agent_reviewed
    workload_identity = var.workload_identity
    static_keys = var.static_keys
    secret_payload_in_state = var.secret_payload_in_state
    private_dns_reviewed = var.private_dns_reviewed
    dependency = terraform_data.storage_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.kms_enabled && var.kms_recovery_tested && var.kms_service_agent_reviewed && var.workload_identity && !var.static_keys && !var.secret_payload_in_state && var.private_dns_reviewed)
      error_message = "production security_contract safeguards required"
    }
  }
}

resource "terraform_data" "operations_contract" {
  input = {
    project_id = var.project_id
    region = var.region
    owner = var.owner
    change_ticket = var.change_ticket
    labels = local.labels
    monitoring_enabled = var.monitoring_enabled
    audit_logs_enabled = var.audit_logs_enabled
    dr_runbook_tested = var.dr_runbook_tested
    rpo_rto_measured = var.rpo_rto_measured
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_approved = var.change_approved
    dependency = terraform_data.security_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.monitoring_enabled && var.audit_logs_enabled && var.dr_runbook_tested && var.rpo_rto_measured && var.dbre_approved && var.security_approved && var.change_approved)
      error_message = "production operations_contract safeguards required"
    }
  }
}
