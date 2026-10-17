variable "environment" {
  type = string
  nullable = false
}
variable "network" {
  type = object({
    id = string
    cidr = string
    environment = string
    owner = string
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
