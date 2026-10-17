resource "terraform_data" "state_boundary" {
  input = {
    environment  = var.environment
    owner        = var.owner
    backend_type = var.backend_type
  }
  lifecycle {
    precondition {
      condition     = var.environment != "prod" || var.backend_type != "local"
      error_message = "production state must not use local backend classification"
    }
  }
}
resource "terraform_data" "audit_contract" {
  input = {
    environment   = var.environment
    owner         = var.owner
    change_ticket = var.change_ticket
    boundary      = terraform_data.state_boundary.output
  }
}
