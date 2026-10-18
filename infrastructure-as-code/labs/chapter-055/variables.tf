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
variable "cluster_context_verified" {
  type = bool
}
variable "state_isolated" {
  type = bool
}
variable "cni_enforced" {
  type = bool
}
variable "csi_ready" {
  type = bool
}
variable "observability_ready" {
  type = bool
}
variable "capacity_reviewed" {
  type = bool
}
variable "dedicated_service_accounts" {
  type = bool
}
variable "rbac_least_privilege" {
  type = bool
}
variable "psa_restricted" {
  type = bool
}
variable "default_deny_network" {
  type = bool
}
variable "dns_db_egress_scoped" {
  type = bool
}
variable "quotas_enforced" {
  type = bool
}
variable "secrets_excluded_from_state" {
  type = bool
}
variable "wildcard_cluster_admin" {
  type = bool
}
variable "provider_chart_pinned" {
  type = bool
}
variable "chart_provenance_reviewed" {
  type = bool
}
variable "crd_staged" {
  type = bool
}
variable "single_gitops_owner" {
  type = bool
}
variable "rollout_tested" {
  type = bool
}
variable "pdb_reviewed" {
  type = bool
}
variable "rollback_tested" {
  type = bool
}
variable "competing_reconciler" {
  type = bool
}
variable "backup_tested" {
  type = bool
}
variable "restore_tested" {
  type = bool
}
variable "rpo_rto_measured" {
  type = bool
}
variable "game_day_completed" {
  type = bool
}
variable "audit_logs_enabled" {
  type = bool
}
variable "security_approved" {
  type = bool
}
variable "dbre_approved" {
  type = bool
}
variable "change_approved" {
  type = bool
}
variable "unapproved_destroy" {
  type = bool
}
variable "unapproved_pvc_delete" {
  type = bool
}
