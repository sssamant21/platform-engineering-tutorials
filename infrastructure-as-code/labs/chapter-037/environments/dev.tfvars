environment = "dev"
owner = "platform-sre"
change_ticket = "CHG-NET-DEV"
vpc_cidr = "10.80.0.0/16"
az_names = ["us-east-1a", "us-east-1b"]
subnets = {
  public_a = { cidr = "10.80.0.0/24", az = "us-east-1a", tier = "public" }
  public_b = { cidr = "10.80.1.0/24", az = "us-east-1b", tier = "public" }
  app_a = { cidr = "10.80.10.0/24", az = "us-east-1a", tier = "application" }
  app_b = { cidr = "10.80.11.0/24", az = "us-east-1b", tier = "application" }
  db_a = { cidr = "10.80.20.0/24", az = "us-east-1a", tier = "database" }
  db_b = { cidr = "10.80.21.0/24", az = "us-east-1b", tier = "database" }
}
flow_logs_enabled = true
s3_endpoint_enabled = true
database_public_ingress = false
