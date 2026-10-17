terraform {
  required_version = ">= 1.5.0"
}
resource "terraform_data" "offline" {
  input = {
    chapter = "009"
    mode    = "offline"
    owner   = "platform-sre"
  }
}
output "offline_record" {
  value = terraform_data.offline.output
}
