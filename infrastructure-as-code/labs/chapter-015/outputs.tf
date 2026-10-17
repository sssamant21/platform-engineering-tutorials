output "service_names" {
  value = sort(keys(terraform_data.service))
}
output "audit_record" {
  value = terraform_data.audit.output
}
