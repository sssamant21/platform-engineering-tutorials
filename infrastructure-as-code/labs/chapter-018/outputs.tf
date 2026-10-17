output "workload_keys" {
  value = sort(keys(terraform_data.workload))
}
output "workload_inventory" {
  value = { for key, instance in terraform_data.workload : key => instance.output }
}
output "audit" {
  value = terraform_data.audit.output
}
