output "network_contract" {
  value = module.network.contract
}
output "database_contract" {
  value = module.database.contract
}
output "application_contract" {
  value = module.application.contract
}
output "change_ticket" {
  value = terraform_data.audit.output.change_ticket
}
