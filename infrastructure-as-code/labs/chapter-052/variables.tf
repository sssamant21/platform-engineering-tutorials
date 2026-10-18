variable "environment" {
  type = string
}
variable "cluster_name" {
  type = string
}
variable "namespace" {
  type = string
}
variable "owner" {
  type = string
}
variable "change_ticket" {
  type = string
}
variable "namespace_owner_verified" {
  type = bool
}
variable "quota_enabled" {
  type = bool
}
variable "limitrange_enabled" {
  type = bool
}
variable "psa_restricted" {
  type = bool
}
variable "namespace_deletion_protected" {
  type = bool
}
variable "dedicated_service_accounts" {
  type = bool
}
variable "rbac_least_privilege" {
  type = bool
}
variable "rbac_scoped_rolebindings" {
  type = bool
}
variable "effective_permissions_tested" {
  type = bool
}
variable "token_automount_disabled" {
  type = bool
}
variable "wildcard_cluster_admin" {
  type = bool
}
variable "default_service_account_used" {
  type = bool
}
variable "default_deny_ingress" {
  type = bool
}
variable "default_deny_egress" {
  type = bool
}
variable "dns_egress_explicit" {
  type = bool
}
variable "database_egress_scoped" {
  type = bool
}
variable "cni_enforcement_tested" {
  type = bool
}
variable "broad_egress" {
  type = bool
}
variable "audit_logs_enabled" {
  type = bool
}
variable "monitoring_enabled" {
  type = bool
}
variable "tenant_cost_labels" {
  type = bool
}
variable "backup_reviewed" {
  type = bool
}
variable "dbre_approved" {
  type = bool
}
variable "security_approved" {
  type = bool
}
variable "change_approved" {
  type = bool
}
variable "unapproved_destroy" {
  type = bool
}
