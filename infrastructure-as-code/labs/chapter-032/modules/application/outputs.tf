output "contract" {
  value = {
    schema_version = 1
    id             = terraform_data.application.id
    environment    = terraform_data.application.output.environment
    database_id    = terraform_data.application.output.database_id
    owner          = terraform_data.application.output.owner
  }
}
