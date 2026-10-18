locals {
  tags = {
    Environment = var.environment
    ManagedBy = "terraform"
    Owner = var.owner
  }
}
resource "terraform_data" "subscription_contract" {
  input = {
    tenant_id = var.tenant_id
    subscription_id = var.subscription_id
    location = var.location
    environment = var.environment
    tags = local.tags
  }
}
resource "terraform_data" "governance_contract" {
  input = {
    oidc_federation_enabled = var.oidc_federation_enabled
    static_client_secret_used = var.static_client_secret_used
    rbac_least_privilege_reviewed = var.rbac_least_privilege_reviewed
    azure_policy_enabled = var.azure_policy_enabled
    subscription_contract_id = terraform_data.subscription_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.oidc_federation_enabled && !var.static_client_secret_used && var.rbac_least_privilege_reviewed && var.azure_policy_enabled)
      error_message = "production requires OIDC, least privilege, Azure Policy and no static secret"
    }
  }
}
resource "terraform_data" "state_contract" {
  input = {
    encrypted = var.state_encrypted
    private = var.state_private
    locking_enabled = var.state_locking_enabled
    governance_id = terraform_data.governance_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.state_encrypted && var.state_private && var.state_locking_enabled)
      error_message = "production state requires encryption, private access and locking"
    }
  }
}
resource "terraform_data" "audit_contract" {
  input = {
    change_ticket = var.change_ticket
    activity_logs_enabled = var.activity_logs_enabled
    state_contract_id = terraform_data.state_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || var.activity_logs_enabled
      error_message = "production requires Azure Activity Logs"
    }
  }
}
