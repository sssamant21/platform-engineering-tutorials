locals {
  tags = {
    Environment = var.environment
    ManagedBy = "terraform"
    Owner = var.owner
  }
}
resource "terraform_data" "data_contract" {
  input = {
    subscription_id = var.subscription_id
    location = var.location
    postgresql_private = var.postgresql_private
    postgresql_tls = var.postgresql_tls
    postgresql_ha = var.postgresql_ha
    sql_private = var.sql_private
    tags = local.tags
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.postgresql_private && var.postgresql_tls && var.postgresql_ha && var.sql_private)
      error_message = "production requires private PostgreSQL/SQL, TLS and PostgreSQL HA"
    }
  }
}
resource "terraform_data" "storage_contract" {
  input = {
    storage_private = var.storage_private
    storage_versioning = var.storage_versioning
    encryption_enabled = var.encryption_enabled
    key_vault_purge_protection = var.key_vault_purge_protection
    data_id = terraform_data.data_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.storage_private && var.storage_versioning && var.encryption_enabled && var.key_vault_purge_protection)
      error_message = "production storage requires private access, versioning, encryption and purge protection"
    }
  }
}
resource "terraform_data" "recovery_contract" {
  input = {
    backup_enabled = var.backup_enabled
    pitr_enabled = var.pitr_enabled
    restore_drill_tested = var.restore_drill_tested
    rpo_minutes = var.rpo_minutes
    rto_minutes = var.rto_minutes
    storage_id = terraform_data.storage_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.backup_enabled && var.pitr_enabled && var.restore_drill_tested && var.rpo_minutes <= 60 && var.rto_minutes <= 240)
      error_message = "production requires backups, PITR, restore drills, RPO <=60m and RTO <=240m"
    }
  }
}
resource "terraform_data" "operations_contract" {
  input = {
    diagnostics_enabled = var.diagnostics_enabled
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_ticket = var.change_ticket
    recovery_id = terraform_data.recovery_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.diagnostics_enabled && var.dbre_approved && var.security_approved)
      error_message = "production requires diagnostics, DBRE and Security approval"
    }
  }
}
