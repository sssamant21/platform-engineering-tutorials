output "service_names" {
  value = sort(keys(terraform_data.service))
}
output "seed_record" {
  value = terraform_data.seed.output
}
