variable "environment" {
  type = string
  default = "dev"
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "owner" {
  type = string
  default = "platform-sre"
  nullable = false
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner must be nonempty"
  }
}
variable "identity_reference" {
  type = string
  default = "oidc://platform/terraform-lab"
  nullable = false
  validation {
    condition = can(regex("^(oidc|role|managed-identity)://", var.identity_reference))
    error_message = "identity_reference must be a non-secret federated identity reference"
  }
}
