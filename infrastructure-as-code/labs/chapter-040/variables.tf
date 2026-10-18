variable "environment" {
  type = string
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "aws_account_id" {
  type = string
  nullable = false
  validation {
    condition = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "account ID must be twelve digits"
  }
}
variable "primary_region" {
  type = string
  nullable = false
  validation {
    condition = contains(["us-east-1", "us-east-2", "us-west-2"], var.primary_region)
    error_message = "approved primary region required"
  }
}
variable "dr_region" {
  type = string
  nullable = false
  validation {
    condition = contains(["us-east-1", "us-east-2", "us-west-2"], var.dr_region)
    error_message = "approved DR region required"
  }
}
variable "owner" {
  type = string
  nullable = false
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner required"
  }
}
variable "change_ticket" {
  type = string
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
variable "rpo_minutes" {
  type = number
  nullable = false
  validation {
    condition = var.rpo_minutes >= 0 && var.rpo_minutes <= 1440
    error_message = "RPO must be 0-1440 minutes"
  }
}
variable "rto_minutes" {
  type = number
  nullable = false
  validation {
    condition = var.rto_minutes > 0 && var.rto_minutes <= 1440
    error_message = "RTO must be 1-1440 minutes"
  }
}
variable "backup_retention_days" {
  type = number
  nullable = false
  validation {
    condition = var.backup_retention_days >= 1 && var.backup_retention_days <= 35 && floor(var.backup_retention_days) == var.backup_retention_days
    error_message = "RDS retention must be 1-35 days"
  }
}
variable "database_multi_az" { type = bool
  nullable = false }
variable "database_encrypted" { type = bool
  nullable = false }
variable "database_deletion_protection" { type = bool
  nullable = false }
variable "s3_versioning_enabled" { type = bool
  nullable = false }
variable "s3_encryption_enabled" { type = bool
  nullable = false }
variable "s3_public_access_blocked" { type = bool
  nullable = false }
variable "ebs_encrypted" { type = bool
  nullable = false }
variable "efs_encrypted" { type = bool
  nullable = false }
variable "backup_restore_tested" { type = bool
  nullable = false }
variable "kms_decrypt_tested" { type = bool
  nullable = false }
variable "cloudwatch_enabled" { type = bool
  nullable = false }
