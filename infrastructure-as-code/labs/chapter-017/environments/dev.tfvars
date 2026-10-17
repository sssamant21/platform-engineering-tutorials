environment = "dev"
service = "patient-api"
owner = "platform-sre"
services = {
  api = { replicas = 2, enabled = true, tier = "frontend" }
  worker = { replicas = 2, enabled = true, tier = "backend" }
}
tags = { cost_center = "lab", managed_by = "terraform" }
