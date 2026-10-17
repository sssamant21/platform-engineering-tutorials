locals {
  owner = "platform-sre"
  metadata = {
    chapter = "013"
    environment = var.environment
    replicas = var.replicas
    owner = local.owner
  }
}
resource "terraform_data" "workload" {
  input = local.metadata
}
resource "terraform_data" "audit" {
  input = {
    source_environment = terraform_data.workload.output.environment
    source_replicas = terraform_data.workload.output.replicas
    event = "execution-lifecycle-lab"
  }
}
