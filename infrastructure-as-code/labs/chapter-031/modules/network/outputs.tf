output "contract" {
  value = {
    id = terraform_data.network.id
    cidr = terraform_data.network.output.cidr
    environment = terraform_data.network.output.environment
    owner = terraform_data.network.output.owner
  }
}
