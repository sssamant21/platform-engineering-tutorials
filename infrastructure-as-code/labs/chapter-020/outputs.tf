output "workload_keys" {
  value = sort(keys(terraform_data.workload))
}
output "audit" {
  value = terraform_data.audit.output
}
