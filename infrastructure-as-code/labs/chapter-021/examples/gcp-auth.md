# GCP authentication review checklist

Prefer Workload Identity Federation or approved service-account impersonation. Verify the effective project, service account, scopes and permissions. Avoid JSON service-account keys. Confirm that the Terraform state backend is authorized separately from provider operations. Use read-only verification first; no cloud apply is part of this offline lab.
