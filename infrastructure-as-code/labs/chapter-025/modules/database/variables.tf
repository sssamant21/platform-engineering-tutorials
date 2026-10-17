variable "environment" {
  type = string
}
variable "owner" {
  type = string
}
variable "network" {
  type = object({
    schema_version = number
    environment    = string
    primary        = string
    secondary      = string
  })
}
variable "replicas" {
  type = number
}
variable "backup_enabled" {
  type = bool
}
variable "encryption_enabled" {
  type = bool
}
variable "deletion_protection" {
  type = bool
}
