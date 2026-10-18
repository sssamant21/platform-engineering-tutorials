locals {
  labels = {
    environment = var.environment
    managed-by = "terraform"
    owner = var.owner
  }
}
resource "terraform_data" "compute_contract" {
  input = {
    project_id = var.project_id
    region = var.region
    mig_regional = var.mig_regional
    mig_autohealing = var.mig_autohealing
    mig_autoscaling = var.mig_autoscaling
    vm_shielded = var.vm_shielded
    vm_public_ip = var.vm_public_ip
    vm_os_login = var.vm_os_login
    labels = local.labels
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.mig_regional && var.mig_autohealing && var.mig_autoscaling && var.vm_shielded && !var.vm_public_ip && var.vm_os_login)
      error_message = "production requires regional autohealing MIG, autoscaling, shielded private VM and OS Login"
    }
  }
}
resource "terraform_data" "gke_contract" {
  input = {
    gke_private_nodes = var.gke_private_nodes
    gke_private_endpoint_reviewed = var.gke_private_endpoint_reviewed
    gke_workload_identity = var.gke_workload_identity
    gke_network_policy = var.gke_network_policy
    gke_release_channel_reviewed = var.gke_release_channel_reviewed
    gke_pdb_reviewed = var.gke_pdb_reviewed
    gke_autoscaling_reviewed = var.gke_autoscaling_reviewed
    static_service_account_keys = var.static_service_account_keys
    compute_id = terraform_data.compute_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.gke_private_nodes && var.gke_private_endpoint_reviewed && var.gke_workload_identity && var.gke_network_policy && var.gke_release_channel_reviewed && var.gke_pdb_reviewed && var.gke_autoscaling_reviewed && !var.static_service_account_keys)
      error_message = "production requires private GKE, workload identity, network policy, safe upgrades and keyless auth"
    }
  }
}
resource "terraform_data" "application_contract" {
  input = {
    app_ingress_tls = var.app_ingress_tls
    app_health_checks = var.app_health_checks
    app_image_digest_pinned = var.app_image_digest_pinned
    app_secret_payload_in_state = var.app_secret_payload_in_state
    db_private_connectivity_reviewed = var.db_private_connectivity_reviewed
    db_connection_pooling_reviewed = var.db_connection_pooling_reviewed
    gke_id = terraform_data.gke_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.app_ingress_tls && var.app_health_checks && var.app_image_digest_pinned && !var.app_secret_payload_in_state && var.db_private_connectivity_reviewed && var.db_connection_pooling_reviewed)
      error_message = "production requires TLS, health checks, immutable images, no secret payloads and DBRE review"
    }
  }
}
resource "terraform_data" "operations_contract" {
  input = {
    monitoring_enabled = var.monitoring_enabled
    audit_logs_enabled = var.audit_logs_enabled
    rollback_tested = var.rollback_tested
    dbre_approved = var.dbre_approved
    security_approved = var.security_approved
    change_ticket = var.change_ticket
    application_id = terraform_data.application_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.monitoring_enabled && var.audit_logs_enabled && var.rollback_tested && var.dbre_approved && var.security_approved && length(trimspace(var.change_ticket)) > 0)
      error_message = "production requires monitoring, audit, rollback, approvals and ticket"
    }
  }
}
