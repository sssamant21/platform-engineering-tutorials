output "network_contract" {
  value = module.network.contract
}
output "database_contract" {
  value = module.database.contract
}
output "application_contract" {
  value = terraform_data.application.output
}
