output "vpc_contract" {
  value = terraform_data.vpc_contract.output
}
output "subnet_contracts" {
  value = { for name, s in terraform_data.subnet_contract : name => s.output }
}
output "routing_contract" {
  value = terraform_data.routing_contract.output
}
output "security_contract" {
  value = terraform_data.security_contract.output
}
