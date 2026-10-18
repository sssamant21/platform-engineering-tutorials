locals {
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = var.owner
  }
}

resource "terraform_data" "compute_contract" {
  input = {
    account_id = var.aws_account_id
    region = var.region
    availability_zones = var.availability_zones
    asg_min = var.asg_min
    asg_desired = var.asg_desired
    asg_max = var.asg_max
    imds_v2_required = var.imds_v2_required
    ebs_encrypted = var.ebs_encrypted
    private_instances = true
    tags = local.tags
  }
  lifecycle {
    precondition {
      condition = var.asg_min <= var.asg_desired && var.asg_desired <= var.asg_max
      error_message = "ASG capacities must satisfy min <= desired <= max"
    }
    precondition {
      condition = var.environment != "prod" || (var.asg_min >= 2 && var.imds_v2_required && var.ebs_encrypted)
      error_message = "production requires two instances, IMDSv2 and encrypted EBS"
    }
  }
}

resource "terraform_data" "alb_contract" {
  input = {
    https_enabled = var.alb_https_enabled
    health_check_path = "/readyz"
    deregistration_delay_seconds = 60
    compute_id = terraform_data.compute_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || var.alb_https_enabled
      error_message = "production ALB requires HTTPS"
    }
  }
}

resource "terraform_data" "eks_contract" {
  input = {
    private_endpoint = var.eks_private_endpoint
    control_plane_logging = var.eks_control_plane_logging
    secrets_encrypted = var.eks_secrets_encrypted
    pod_identity_enabled = var.pod_identity_enabled
    multi_az = length(var.availability_zones) >= 2
    alb_contract_id = terraform_data.alb_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (var.eks_private_endpoint && var.eks_control_plane_logging && var.eks_secrets_encrypted && var.pod_identity_enabled)
      error_message = "production EKS requires private endpoint, logging, encryption and pod identity"
    }
  }
}

resource "terraform_data" "audit_contract" {
  input = {
    change_ticket = var.change_ticket
    cloudwatch_enabled = var.cloudwatch_enabled
    eks_contract_id = terraform_data.eks_contract.id
  }
  lifecycle {
    precondition {
      condition = var.environment != "prod" || var.cloudwatch_enabled
      error_message = "production requires CloudWatch monitoring"
    }
  }
}
