terraform {
  required_version = ">= 1.5.0"
}

resource "terraform_data" "workstation" {
  input = {
    environment = "lab"
    toolchain   = "ready"
    owner       = "platform-sre"
  }
}

output "workstation_check" {
  value = terraform_data.workstation.output
}
