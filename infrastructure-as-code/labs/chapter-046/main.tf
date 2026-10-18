locals {
  labels = {
    environment = var.environment
    managed-by = "terraform"
    owner = var.owner
  }
}
resource "terraform_data" "project_contract" {
  input = {
    project_id = var.project_id
    project_number = var.project_number
    region = var.region
    billing_reviewed = var.billing_reviewed
    org_policy_reviewed = var.org_policy_reviewed
    service_apis_reviewed = var.service_apis_reviewed
    quota_reviewed = var.quota_reviewed
    labels = local.labels
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.billing_reviewed && var.org_policy_reviewed && var.service_apis_reviewed && var.quota_reviewed)
      error_message = "production requires billing, organization policy, APIs and quota review"
    }
  }
}
resource "terraform_data" "identity_contract" {
  input = {
    wif_enabled = var.wif_enabled
    static_service_account_key_used = var.static_service_account_key_used
    least_privilege_reviewed = var.least_privilege_reviewed
    project_id = terraform_data.project_contract.output.project_id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.wif_enabled && !var.static_service_account_key_used && var.least_privilege_reviewed)
      error_message = "production requires WIF, no static keys and least privilege"
    }
  }
}
resource "terraform_data" "state_contract" {
  input = {
    gcs_state_private = var.gcs_state_private
    gcs_state_versioning = var.gcs_state_versioning
    gcs_state_encrypted = var.gcs_state_encrypted
    gcs_state_locking = var.gcs_state_locking
    identity_id = terraform_data.identity_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.gcs_state_private && var.gcs_state_versioning && var.gcs_state_encrypted && var.gcs_state_locking)
      error_message = "production requires secure private versioned and locked GCS state"
    }
  }
}
resource "terraform_data" "operations_contract" {
  input = {
    audit_logs_enabled = var.audit_logs_enabled
    budget_alerts_enabled = var.budget_alerts_enabled
    security_approved = var.security_approved
    change_ticket = var.change_ticket
    state_id = terraform_data.state_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.audit_logs_enabled && var.budget_alerts_enabled && var.security_approved)
      error_message = "production requires audit, budgets and security approval"
    }
  }
}
