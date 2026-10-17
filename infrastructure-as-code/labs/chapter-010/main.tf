terraform {
  required_version = ">= 1.5.0"
}

resource "terraform_data" "readiness" {
  input = {
    chapter     = "010"
    environment = "lab"
    owner       = "platform-sre"
    readiness   = "preflight"
  }
}

output "readiness_record" {
  value = terraform_data.readiness.output
}
