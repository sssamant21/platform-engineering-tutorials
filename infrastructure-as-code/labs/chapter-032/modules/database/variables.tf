variable "environment" {
  type = string
  nullable = false
}
variable "network" {
  type = object({
    schema_version = number
    id             = string
    environment    = string
    cidr           = string
    owner          = string
  })
  nullable = false
}
variable "replicas" {
  type = number
  nullable = false
  validation {
    condition = var.replicas >= 1 && floor(var.replicas) == var.replicas
    error_message = "replicas must be positive integer"
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
variable "settings" {
  type = object({
    maintenance_window = optional(string, "sun-03:00")
    monitoring_enabled = optional(bool, true)
  })
  default = {}
  nullable = false
}
