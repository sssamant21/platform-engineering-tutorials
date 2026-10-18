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
variable "oidc_subject" {
  type = string
  nullable = false
  validation {
    condition = startswith(var.oidc_subject, "repo:") && !endswith(var.oidc_subject, "*")
    error_message = "explicit GitHub repository OIDC subject required"
  }
}
variable "oidc_audience" {
  type = string
  nullable = false
  validation {
    condition = var.oidc_audience == "sts.amazonaws.com"
    error_message = "OIDC audience must be sts.amazonaws.com"
  }
}
variable "kms_rotation_enabled" {
  type = bool
  nullable = false
}
variable "kms_deletion_window_days" {
  type = number
  nullable = false
  validation {
    condition = var.kms_deletion_window_days >= 7 && var.kms_deletion_window_days <= 30 && floor(var.kms_deletion_window_days) == var.kms_deletion_window_days
    error_message = "KMS deletion window must be 7-30 days"
  }
}
variable "secret_rotation_enabled" {
  type = bool
  nullable = false
}
variable "cloudtrail_enabled" {
  type = bool
  nullable = false
}
