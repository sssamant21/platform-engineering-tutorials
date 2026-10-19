package iac.security
import rego.v1
default allow := false
allow if {
  input.environment == "staging"
  input.source_signed == true
  input.plan_digest_verified == true
  input.destructive_changes == 0
  input.state_encrypted == true
}
