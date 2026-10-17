resource "terraform_data" "application" {
  input = {
    environment = var.environment
    database_id = var.database.id
    owner = var.owner
  }
  lifecycle {
    precondition {
      condition = var.environment == var.database.environment
      error_message = "application and database environment must match"
    }
  }
}
