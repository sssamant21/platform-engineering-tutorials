terraform {
  required_version = ">= 1.5.0"
}

resource "terraform_data" "workspace_example" {
  input = {
    workspace = terraform.workspace
    owner     = "training"
  }
}

output "workspace" {
  value = terraform_data.workspace_example.output
}
