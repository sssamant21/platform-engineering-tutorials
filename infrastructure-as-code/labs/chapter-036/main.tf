locals {
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = var.owner
    CostCenter  = var.cost_center
  }
}

resource "terraform_data" "aws_identity_contract" {
  input = {
    account_id    = var.aws_account_id
    environment   = var.environment
    change_ticket = var.change_ticket
    tags          = local.tags
  }
}

resource "terraform_data" "region_contract" {
  input = {
    primary_region = var.primary_region
    dr_region      = var.dr_region
  }
  lifecycle {
    precondition {
      condition     = var.primary_region != var.dr_region
      error_message = "DR region must differ from primary region"
    }
  }
}

resource "terraform_data" "workload_contract" {
  input = {
    account_id         = terraform_data.aws_identity_contract.output.account_id
    primary_region     = terraform_data.region_contract.output.primary_region
    database_replicas  = var.database_replicas
    backup_enabled     = var.backup_enabled
    encryption_enabled = var.encryption_enabled
    multi_az_enabled   = var.multi_az_enabled
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.database_replicas >= 3 && var.backup_enabled && var.encryption_enabled && var.multi_az_enabled)
      error_message = "production requires three replicas, backup, encryption and Multi-AZ"
    }
  }
}
