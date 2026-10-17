output "metadata" {
  value = terraform_data.metadata.output
}
output "consumer" {
  value = terraform_data.consumer.output
}
output "zone_index" {
  value = local.zone_index
}
