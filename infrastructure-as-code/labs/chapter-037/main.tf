locals {
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = var.owner
  }
  subnet_azs = distinct([for s in values(var.subnets) : s.az])
  database_subnets = [for name, s in var.subnets : name if s.tier == "database"]
}

resource "terraform_data" "vpc_contract" {
  input = {
    cidr         = var.vpc_cidr
    environment  = var.environment
    change_ticket = var.change_ticket
    tags         = local.tags
  }
}

resource "terraform_data" "subnet_contract" {
  for_each = var.subnets
  input = {
    name = each.key
    cidr = each.value.cidr
    az   = each.value.az
    tier = each.value.tier
    vpc_cidr = terraform_data.vpc_contract.output.cidr
  }
  lifecycle {
    precondition {
      condition = contains(var.az_names, each.value.az)
      error_message = "subnet AZ must be declared"
    }
    precondition {
      condition = can(cidrhost(var.vpc_cidr, 0)) && can(cidrhost(each.value.cidr, 0))
      error_message = "subnet CIDR must be valid"
    }
  }
}

resource "terraform_data" "routing_contract" {
  input = {
    public_default_route = "internet-gateway"
    application_default_route = "same-az-nat-or-endpoint"
    database_default_route = "none"
    s3_endpoint_enabled = var.s3_endpoint_enabled
    subnet_ids = [for s in terraform_data.subnet_contract : s.id]
  }
}

resource "terraform_data" "security_contract" {
  input = {
    flow_logs_enabled = var.flow_logs_enabled
    database_public_ingress = var.database_public_ingress
    database_subnets = local.database_subnets
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.flow_logs_enabled && var.s3_endpoint_enabled && !var.database_public_ingress && length(local.database_subnets) >= 2)
      error_message = "production requires flow logs, S3 endpoint, private DB and multi-AZ DB subnets"
    }
  }
}
