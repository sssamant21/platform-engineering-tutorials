resource "terraform_data" "application" {
  input = {
    environment = var.environment
    database_id = var.database.id
    owner       = var.owner
  }
  lifecycle {
    precondition {
      condition = var.database.schema_version == 1 && var.database.environment == var.environment
      error_message = "database contract version/environment mismatch"
    }
  }
}
