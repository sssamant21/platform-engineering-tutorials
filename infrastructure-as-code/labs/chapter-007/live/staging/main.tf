terraform {
  required_version = ">= 1.5.0"
}

module "metadata" {
  source      = "../../modules/metadata"
  environment = "staging"
  owner       = "platform-sre"
  service     = "training"
}

output "metadata" {
  value = module.metadata.record
}
