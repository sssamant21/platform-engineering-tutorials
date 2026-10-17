variable "environment" { type = string }
variable "owner" { type = string }
variable "network" {
  type = object({ schema_version = number, environment = string, primary = string, secondary = string })
}
variable "backup_enabled" { type = bool }
variable "encrypted" { type = bool }
