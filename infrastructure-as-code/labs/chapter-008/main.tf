terraform {
  required_version = ">= 1.5.0"
}

resource "terraform_data" "toolchain" {
  input = {
    environment = "lab"
    engine      = "terraform-or-opentofu"
    owner       = "platform-sre"
  }
}

output "toolchain_record" {
  value = terraform_data.toolchain.output
}
