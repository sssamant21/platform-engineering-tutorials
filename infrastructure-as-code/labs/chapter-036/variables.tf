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
    error_message = "AWS account ID must be 12 digits"
  }
}
variable "primary_region" {
  type = string
  nullable = false
  validation {
    condition = contains(["us-east-1", "us-east-2", "us-west-2"], var.primary_region)
    error_message = "unapproved primary region"
  }
}
variable "dr_region" {
  type = string
  nullable = false
  validation {
    condition = contains(["us-east-1", "us-east-2", "us-west-2"], var.dr_region)
    error_message = "unapproved DR region"
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
variable "cost_center" {
  type = string
  nullable = false
  validation {
    condition = length(trimspace(var.cost_center)) > 0
    error_message = "cost center required"
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
variable "database_replicas" {
  type = number
  nullable = false
  validation {
    condition = var.database_replicas >= 1 && floor(var.database_replicas) == var.database_replicas
    error_message = "positive integer replicas required"
  }
}
variable "backup_enabled" {
  type = bool
  nullable = false
}
variable "encryption_enabled" {
  type = bool
  nullable = false
}
variable "multi_az_enabled" {
  type = bool
  nullable = false
}
