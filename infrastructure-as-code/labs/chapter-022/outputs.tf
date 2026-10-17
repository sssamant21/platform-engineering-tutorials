output "dependency_inventory" {
  value = {
    foundation = terraform_data.foundation.output
    database = terraform_data.database.output
    application = terraform_data.application.output
    monitoring = terraform_data.monitoring.output
    audit = terraform_data.audit.output
  }
}
