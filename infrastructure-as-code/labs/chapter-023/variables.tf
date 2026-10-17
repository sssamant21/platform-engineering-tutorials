variable "environment" {
  type = string
  default = "dev"
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "owner" {
  type = string
  default = "platform-sre"
  nullable = false
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner is required"
  }
}
variable "change_ticket" {
  type = string
  default = "CHG-DEMO-023"
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
variable "subnet_ids" {
  type = map(string)
  default = { primary = "subnet-lab-a", secondary = "subnet-lab-b" }
  nullable = false
  validation {
    condition = contains(keys(var.subnet_ids), "primary") && contains(keys(var.subnet_ids), "secondary") && alltrue([for id in values(var.subnet_ids) : length(trimspace(id)) > 0])
    error_message = "primary and secondary subnet IDs must be present and nonempty"
  }
}
variable "database_backup_enabled" { type = bool, default = true, nullable = false }
variable "database_encrypted" { type = bool, default = true, nullable = false }
