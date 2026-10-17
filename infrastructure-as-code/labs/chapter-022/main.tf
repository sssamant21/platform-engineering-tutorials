resource "terraform_data" "foundation" {
  input = { environment = var.environment, owner = var.owner }
}
resource "terraform_data" "database" {
  input = {
    foundation_environment = terraform_data.foundation.output.environment
    name = "db"
  }
}
resource "terraform_data" "application" {
  input = {
    database_name = terraform_data.database.output.name
    name = "api"
  }
}
resource "terraform_data" "monitoring" {
  input = {
    application_name = terraform_data.application.output.name
    name = "monitor"
  }
}
resource "terraform_data" "audit" {
  input = {
    change_ticket = var.change_ticket
    owner = var.owner
    environment = var.environment
  }
  depends_on = [terraform_data.monitoring]
}
