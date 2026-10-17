resource "terraform_data" "network" {
  input = {
    environment = var.environment
    cidr        = var.cidr
    owner       = var.owner
  }
}
