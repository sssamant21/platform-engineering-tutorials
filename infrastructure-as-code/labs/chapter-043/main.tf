locals {
  tags = {
    Environment = var.environment
    ManagedBy = "terraform"
    Owner = var.owner
  }
}
resource "terraform_data" "identity_contract" {
  input = {
    tenant_id = var.tenant_id
    subscription_id = var.subscription_id
    oidc_federation_enabled = var.oidc_federation_enabled
    static_client_secret_used = var.static_client_secret_used
    managed_identity_enabled = var.managed_identity_enabled
    tags = local.tags
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.oidc_federation_enabled && !var.static_client_secret_used && var.managed_identity_enabled)
      error_message = "production requires OIDC, managed identity and no static secret"
    }
  }
}
resource "terraform_data" "rbac_contract" {
  input = {
    rbac_least_privilege_reviewed = var.rbac_least_privilege_reviewed
    privileged_role_assignment_used = var.privileged_role_assignment_used
    identity_id = terraform_data.identity_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.rbac_least_privilege_reviewed && !var.privileged_role_assignment_used)
      error_message = "production RBAC requires least privilege and no privileged assignment"
    }
  }
}
resource "terraform_data" "vault_contract" {
  input = {
    key_vault_rbac_enabled = var.key_vault_rbac_enabled
    key_vault_private = var.key_vault_private
    key_vault_purge_protection = var.key_vault_purge_protection
    secret_rotation_enabled = var.secret_rotation_enabled
    cmk_recovery_tested = var.cmk_recovery_tested
    rbac_id = terraform_data.rbac_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.key_vault_rbac_enabled && var.key_vault_private && var.key_vault_purge_protection && var.secret_rotation_enabled && var.cmk_recovery_tested)
      error_message = "production vault requires RBAC, private access, purge protection, rotation and CMK recovery"
    }
  }
}
resource "terraform_data" "audit_contract" {
  input = {
    change_ticket = var.change_ticket
    state_encrypted = var.state_encrypted
    state_private = var.state_private
    audit_logs_enabled = var.audit_logs_enabled
    vault_id = terraform_data.vault_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.state_encrypted && var.state_private && var.audit_logs_enabled)
      error_message = "production requires secure state and audit logs"
    }
  }
}
