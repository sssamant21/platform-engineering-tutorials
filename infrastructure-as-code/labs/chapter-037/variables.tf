variable "environment" {
  type = string
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
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
variable "vpc_cidr" {
  type = string
  nullable = false
  validation {
    condition = can(cidrhost(var.vpc_cidr, 0))
    error_message = "valid VPC CIDR required"
  }
}
variable "az_names" {
  type = list(string)
  nullable = false
  validation {
    condition = length(var.az_names) >= 2 && length(distinct(var.az_names)) == length(var.az_names)
    error_message = "at least two distinct AZs required"
  }
}
variable "subnets" {
  type = map(object({
    cidr = string
    az = string
    tier = string
  }))
  nullable = false
  validation {
    condition = alltrue([for s in values(var.subnets) : can(cidrhost(s.cidr, 0)) && contains(["public", "application", "database"], s.tier)])
    error_message = "valid subnet CIDRs and tiers required"
  }
}
variable "flow_logs_enabled" {
  type = bool
  nullable = false
}
variable "s3_endpoint_enabled" {
  type = bool
  nullable = false
}
variable "database_public_ingress" {
  type = bool
  nullable = false
}
