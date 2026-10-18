locals {
  tags = {
    Environment = var.environment
    ManagedBy = "terraform"
    Owner = var.owner
  }
}
resource "terraform_data" "compute_contract" {
  input = {
    subscription_id = var.subscription_id
    location = var.location
    node_vm_size = var.node_vm_size
    node_count = var.node_count
    availability_zones = var.availability_zones
    tags = local.tags
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.node_count >= 3 && length(distinct(var.availability_zones)) >= 2)
      error_message = "production requires at least three nodes and two distinct zones"
    }
  }
}
resource "terraform_data" "aks_contract" {
  input = {
    aks_private_cluster = var.aks_private_cluster
    workload_identity_enabled = var.workload_identity_enabled
    oidc_issuer_enabled = var.oidc_issuer_enabled
    acr_private = var.acr_private
    compute_id = terraform_data.compute_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.aks_private_cluster && var.workload_identity_enabled && var.oidc_issuer_enabled && var.acr_private)
      error_message = "production AKS requires private API, OIDC, workload identity and private ACR"
    }
  }
}
resource "terraform_data" "application_contract" {
  input = {
    image_digest_pinned = var.image_digest_pinned
    pdb_enabled = var.pdb_enabled
    autoscaling_enabled = var.autoscaling_enabled
    private_database_access = var.private_database_access
    aks_id = terraform_data.aks_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.image_digest_pinned && var.pdb_enabled && var.autoscaling_enabled && var.private_database_access)
      error_message = "production applications require digest pinning, PDB, autoscaling and private DB"
    }
  }
}
resource "terraform_data" "operations_contract" {
  input = {
    diagnostics_enabled = var.diagnostics_enabled
    upgrade_reviewed = var.upgrade_reviewed
    change_ticket = var.change_ticket
    application_id = terraform_data.application_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.diagnostics_enabled && var.upgrade_reviewed)
      error_message = "production requires diagnostics and upgrade review"
    }
  }
}
