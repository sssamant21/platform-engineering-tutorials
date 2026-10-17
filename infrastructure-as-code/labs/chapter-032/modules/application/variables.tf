variable "environment" {
  type = string
  nullable = false
}
variable "database" {
  type = object({
    schema_version     = number
    id                 = string
    environment        = string
    network_id         = string
    replicas           = number
    backup_enabled     = bool
    encryption_enabled = bool
  })
  nullable = false
}
variable "owner" {
  type = string
  nullable = false
}
