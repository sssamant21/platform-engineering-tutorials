variable "environment" {
  type = string
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "project_id" {
  type = string
  validation {
    condition = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "valid GCP project ID required"
  }
}
variable "region" {
  type = string
  validation {
    condition = contains(["us-central1", "us-east1", "us-east4", "us-west1"], var.region)
    error_message = "approved region required"
  }
}
variable "owner" {
  type = string
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner required"
  }
}
variable "change_ticket" {
  type = string
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
variable "vpc_custom_mode" { type = bool }
variable "subnet_cidr" { type = string }
variable "pod_cidr" { type = string }
variable "services_cidr" { type = string }
variable "private_google_access" { type = bool }
variable "firewall_restricted" { type = bool }
variable "firewall_logging" { type = bool }
variable "ssh_public_ingress" { type = bool }
variable "database_public_ingress" { type = bool }
variable "cloud_nat_enabled" { type = bool }
variable "private_service_connect_reviewed" { type = bool }
variable "cloud_dns_reviewed" { type = bool }
variable "hybrid_routes_reviewed" { type = bool }
variable "vpc_flow_logs_enabled" { type = bool }
variable "monitoring_enabled" { type = bool }
variable "dbre_approved" { type = bool }
variable "security_approved" { type = bool }
