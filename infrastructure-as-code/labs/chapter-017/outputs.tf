output "services" {
  value = { for name, resource in terraform_data.service : name => resource.output }
}
output "audit" {
  value = terraform_data.audit.output
}
