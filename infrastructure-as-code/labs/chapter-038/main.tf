locals {
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = var.owner
  }
}

resource "terraform_data" "identity_contract" {
  input = {
    account_id = var.aws_account_id
    oidc_subject = var.oidc_subject
    oidc_audience = var.oidc_audience
    short_lived = true
    tags = local.tags
  }
}

resource "terraform_data" "kms_contract" {
  input = {
    rotation_enabled = var.kms_rotation_enabled
    deletion_window_days = var.kms_deletion_window_days
    environment = var.environment
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.kms_rotation_enabled && var.kms_deletion_window_days >= 14)
      error_message = "production requires KMS rotation and at least 14-day deletion window"
    }
  }
}

resource "terraform_data" "secrets_contract" {
  input = {
    secret_values_in_state = false
    rotation_enabled = var.secret_rotation_enabled
    kms_contract_id = terraform_data.kms_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || var.secret_rotation_enabled
      error_message = "production requires secret rotation"
    }
  }
}

resource "terraform_data" "audit_contract" {
  input = {
    change_ticket = var.change_ticket
    cloudtrail_enabled = var.cloudtrail_enabled
    identity_contract_id = terraform_data.identity_contract.id
    secrets_contract_id = terraform_data.secrets_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || var.cloudtrail_enabled
      error_message = "production requires CloudTrail"
    }
  }
}
