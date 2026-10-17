variable "environment" {
  type = string
  nullable = false
}
variable "cidr" {
  type = string
  nullable = false
  validation {
    condition = can(cidrhost(var.cidr, 0))
    error_message = "cidr must be valid"
  }
}
variable "owner" {
  type = string
  nullable = false
}
variable "labels" {
  type = object({
    team = optional(string, "platform")
    cost_center = optional(string, "sandbox")
  })
  default = {}
  nullable = false
}
