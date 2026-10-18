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
variable "region" {
  type = string
  nullable = false
  validation {
    condition = contains(["us-east-1", "us-east-2", "us-west-2"], var.region)
    error_message = "approved AWS region required"
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
variable "availability_zones" {
  type = list(string)
  nullable = false
  validation {
    condition = length(var.availability_zones) >= 2 && length(distinct(var.availability_zones)) == length(var.availability_zones)
    error_message = "at least two distinct AZs required"
  }
}
variable "asg_min" {
  type = number
  nullable = false
  validation {
    condition = var.asg_min >= 1 && floor(var.asg_min) == var.asg_min
    error_message = "ASG minimum must be positive integer"
  }
}
variable "asg_desired" {
  type = number
  nullable = false
  validation {
    condition = var.asg_desired >= 1 && floor(var.asg_desired) == var.asg_desired
    error_message = "ASG desired must be positive integer"
  }
}
variable "asg_max" {
  type = number
  nullable = false
  validation {
    condition = var.asg_max >= 1 && floor(var.asg_max) == var.asg_max
    error_message = "ASG maximum must be positive integer"
  }
}
variable "imds_v2_required" { type = bool, nullable = false }
variable "ebs_encrypted" { type = bool, nullable = false }
variable "alb_https_enabled" { type = bool, nullable = false }
variable "eks_private_endpoint" { type = bool, nullable = false }
variable "eks_control_plane_logging" { type = bool, nullable = false }
variable "eks_secrets_encrypted" { type = bool, nullable = false }
variable "pod_identity_enabled" { type = bool, nullable = false }
variable "cloudwatch_enabled" { type = bool, nullable = false }
