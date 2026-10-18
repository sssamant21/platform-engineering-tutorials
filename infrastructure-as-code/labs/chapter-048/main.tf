locals {
  labels = {
    environment = var.environment
    managed-by = "terraform"
    owner = var.owner
  }
}
resource "terraform_data" "iam_contract" {
  input = {
    project_id = var.project_id
    region = var.region
    least_privilege = var.least_privilege
    primitive_roles_used = var.primitive_roles_used
    iam_deny_reviewed = var.iam_deny_reviewed
    org_policy_reviewed = var.org_policy_reviewed
    labels = local.labels
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.least_privilege && !var.primitive_roles_used && var.iam_deny_reviewed && var.org_policy_reviewed)
      error_message = "production requires least privilege, no primitive roles, deny and org policy review"
    }
  }
}
resource "terraform_data" "wif_contract" {
  input = {
    wif_enabled = var.wif_enabled
    static_service_account_keys = var.static_service_account_keys
    oidc_trust_reviewed = var.oidc_trust_reviewed
    impersonation_scoped = var.impersonation_scoped
    iam_id = terraform_data.iam_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.wif_enabled && !var.static_service_account_keys && var.oidc_trust_reviewed && var.impersonation_scoped)
      error_message = "production requires scoped keyless WIF and impersonation"
    }
  }
}
resource "terraform_data" "kms_secrets_contract" {
  input = {
    kms_enabled = var.kms_enabled
    kms_rotation_reviewed = var.kms_rotation_reviewed
    kms_recovery_tested = var.kms_recovery_tested
    secret_metadata_only = var.secret_metadata_only
    secret_payload_in_state = var.secret_payload_in_state
    wif_id = terraform_data.wif_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.kms_enabled && var.kms_rotation_reviewed && var.kms_recovery_tested && var.secret_metadata_only && !var.secret_payload_in_state)
      error_message = "production requires KMS recovery and no secret payload in state"
    }
  }
}
resource "terraform_data" "operations_contract" {
  input = {
    gcs_state_private = var.gcs_state_private
    gcs_state_versioned = var.gcs_state_versioned
    audit_logs_enabled = var.audit_logs_enabled
    security_approved = var.security_approved
    dbre_approved = var.dbre_approved
    change_ticket = var.change_ticket
    security_id = terraform_data.kms_secrets_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.gcs_state_private && var.gcs_state_versioned && var.audit_logs_enabled && var.security_approved && var.dbre_approved)
      error_message = "production requires protected state, audit and approvals"
    }
  }
}
