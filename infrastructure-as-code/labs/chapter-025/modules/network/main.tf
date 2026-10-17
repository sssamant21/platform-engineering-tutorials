resource "terraform_data" "contract" {
  input = {
    schema_version = 1
    environment    = var.environment
    primary        = var.subnet_ids["primary"]
    secondary      = var.subnet_ids["secondary"]
  }
}
