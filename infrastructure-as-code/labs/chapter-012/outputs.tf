output "service_records" {
  value = { for name, resource in terraform_data.service : name => resource.output }
}
output "audit_record" {
  value = terraform_data.audit.output
}
