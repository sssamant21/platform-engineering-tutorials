environment = "prod"
service = "patient-api"
owner = "dbre-team"
services = {
  api = { replicas = 3, enabled = true, tier = "frontend" }
  worker = { replicas = 3, enabled = true, tier = "backend" }
}
tags = { cost_center = "demo-prod", managed_by = "terraform" }
