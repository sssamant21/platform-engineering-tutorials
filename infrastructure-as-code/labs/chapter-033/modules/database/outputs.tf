output "contract" {
  value = {
    schema_version     = 1
    id                 = terraform_data.database.id
    environment        = terraform_data.database.output.environment
    network_id         = terraform_data.database.output.network_id
    replicas           = terraform_data.database.output.replicas
    backup_enabled     = terraform_data.database.output.backup_enabled
    encryption_enabled = terraform_data.database.output.encryption_enabled
  }
}
