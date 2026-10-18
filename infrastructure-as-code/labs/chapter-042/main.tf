locals {
  tags = {
    Environment = var.environment
    ManagedBy = "terraform"
    Owner = var.owner
  }
  subnet_cidrs = [var.aks_subnet_cidr, var.app_subnet_cidr, var.endpoint_subnet_cidr, var.database_subnet_cidr]
}
resource "terraform_data" "vnet_contract" {
  input = {
    subscription_id = var.subscription_id
    location = var.location
    vnet_cidr = var.vnet_cidr
    subnet_cidrs = local.subnet_cidrs
    tags = local.tags
  }
  lifecycle {
    precondition {
      condition = length(distinct(local.subnet_cidrs)) == 4
      error_message = "subnet CIDRs must be distinct; Python gate checks full overlap"
    }
  }
}
resource "terraform_data" "security_contract" {
  input = {
    nsg_reviewed = var.nsg_reviewed
    udr_reviewed = var.udr_reviewed
    vnet_id = terraform_data.vnet_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.nsg_reviewed && var.udr_reviewed)
      error_message = "production NSG and UDR require review"
    }
  }
}
resource "terraform_data" "private_connectivity_contract" {
  input = {
    private_endpoint_enabled = var.private_endpoint_enabled
    private_dns_linked = var.private_dns_linked
    database_subnet_delegated = var.database_subnet_delegated
    public_database_access_disabled = var.public_database_access_disabled
    security_id = terraform_data.security_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.private_endpoint_enabled && var.private_dns_linked && var.database_subnet_delegated && var.public_database_access_disabled)
      error_message = "production requires reviewed private connectivity and no public database access"
    }
  }
}
resource "terraform_data" "observability_contract" {
  input = {
    flow_logs_enabled = var.flow_logs_enabled
    change_ticket = var.change_ticket
    connectivity_id = terraform_data.private_connectivity_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || var.flow_logs_enabled
      error_message = "production requires network observability"
    }
  }
}
