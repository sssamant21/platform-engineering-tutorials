output "contract" {
  value = {
    schema_version = 1
    id             = terraform_data.network.id
    environment    = terraform_data.network.output.environment
    cidr           = terraform_data.network.output.cidr
    owner          = terraform_data.network.output.owner
  }
}
