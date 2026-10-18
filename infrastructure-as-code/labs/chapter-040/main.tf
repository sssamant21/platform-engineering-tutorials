locals {
  tags = {
    Environment = var.environment
    ManagedBy = "terraform"
    Owner = var.owner
  }
}
resource "terraform_data" "database_contract" {
  input = {
    account_id = var.aws_account_id
    primary_region = var.primary_region
    multi_az = var.database_multi_az
    encrypted = var.database_encrypted
    deletion_protection = var.database_deletion_protection
    backup_retention_days = var.backup_retention_days
    tags = local.tags
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.database_multi_az && var.database_encrypted && var.database_deletion_protection && var.backup_retention_days >= 7)
      error_message = "production requires multi-AZ, encryption, deletion protection and >=7-day backup retention"
    }
  }
}
resource "terraform_data" "object_storage_contract" {
  input = {
    versioning_enabled = var.s3_versioning_enabled
    encryption_enabled = var.s3_encryption_enabled
    public_access_blocked = var.s3_public_access_blocked
    database_id = terraform_data.database_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.s3_versioning_enabled && var.s3_encryption_enabled && var.s3_public_access_blocked)
      error_message = "production S3 requires versioning, encryption and public access block"
    }
  }
}
resource "terraform_data" "volume_contract" {
  input = {
    ebs_encrypted = var.ebs_encrypted
    efs_encrypted = var.efs_encrypted
    object_storage_id = terraform_data.object_storage_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.ebs_encrypted && var.efs_encrypted)
      error_message = "production EBS/EFS must be encrypted"
    }
  }
}
resource "terraform_data" "recovery_contract" {
  input = {
    dr_region = var.dr_region
    rpo_minutes = var.rpo_minutes
    rto_minutes = var.rto_minutes
    backup_restore_tested = var.backup_restore_tested
    kms_decrypt_tested = var.kms_decrypt_tested
    cloudwatch_enabled = var.cloudwatch_enabled
    change_ticket = var.change_ticket
    volume_id = terraform_data.volume_contract.id
  }
  lifecycle {
    precondition {
      condition = var.dr_region != var.primary_region
      error_message = "DR region must differ from primary region"
    }
    precondition {
      condition = var.environment != "prod" || (var.backup_restore_tested && var.kms_decrypt_tested && var.cloudwatch_enabled)
      error_message = "production requires restore, KMS and observability attestations"
    }
  }
}
