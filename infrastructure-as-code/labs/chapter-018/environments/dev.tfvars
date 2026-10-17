environment = "dev"
owner       = "platform-sre"
zones       = ["a", "b"]
services = {
  api    = { replicas = 2, enabled = true, tier = "frontend" }
  worker = { replicas = 2, enabled = true, tier = "backend" }
}
tags = { cost_center = "demo", managed_by = "terraform" }
