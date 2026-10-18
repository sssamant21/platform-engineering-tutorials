locals {
  labels = {
    environment = var.environment
    managed-by = "terraform"
    owner = var.owner
  }
}
resource "terraform_data" "vpc_contract" {
  input = {
    project_id = var.project_id
    region = var.region
    custom_mode = var.vpc_custom_mode
    subnet_cidr = var.subnet_cidr
    pod_cidr = var.pod_cidr
    services_cidr = var.services_cidr
    private_google_access = var.private_google_access
    labels = local.labels
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.vpc_custom_mode && var.private_google_access)
      error_message = "production requires custom-mode VPC and Private Google Access"
    }
  }
}
resource "terraform_data" "firewall_contract" {
  input = {
    firewall_restricted = var.firewall_restricted
    firewall_logging = var.firewall_logging
    ssh_public_ingress = var.ssh_public_ingress
    database_public_ingress = var.database_public_ingress
    vpc_id = terraform_data.vpc_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.firewall_restricted && var.firewall_logging && !var.ssh_public_ingress && !var.database_public_ingress)
      error_message = "production requires restricted logged firewalls and no public SSH/database ingress"
    }
  }
}
resource "terraform_data" "connectivity_contract" {
  input = {
    cloud_nat_enabled = var.cloud_nat_enabled
    private_service_connect_reviewed = var.private_service_connect_reviewed
    cloud_dns_reviewed = var.cloud_dns_reviewed
    hybrid_routes_reviewed = var.hybrid_routes_reviewed
    firewall_id = terraform_data.firewall_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.cloud_nat_enabled && var.private_service_connect_reviewed && var.cloud_dns_reviewed && var.hybrid_routes_reviewed)
      error_message = "production requires NAT, private service, DNS and hybrid route review"
    }
  }
}
resource "terraform_data" "operations_contract" {
  input = {
    vpc_flow_logs_enabled = var.vpc_flow_logs_enabled
    monitoring_enabled = var.monitoring_enabled
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_ticket = var.change_ticket
    connectivity_id = terraform_data.connectivity_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.vpc_flow_logs_enabled && var.monitoring_enabled && var.dbre_approved && var.security_approved)
      error_message = "production requires flow logs, monitoring, DBRE and Security approval"
    }
  }
}
