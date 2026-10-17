terraform {
  required_version = ">= 1.5.0"
}

module "metadata" {
  source      = "../../modules/metadata"
  environment = "dev"
  owner       = "platform-sre"
  service     = "training"
}

output "metadata" {
  value = module.metadata.record
}
