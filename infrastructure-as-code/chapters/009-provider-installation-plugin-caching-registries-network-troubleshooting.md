# Chapter 009 — Provider Installation, Plugin Caching, Registries and Network Troubleshooting

**Part 02 — Development Environment and Tooling** · **Audience:** SRE/DBRE, DevOps, Platform Engineering · **Level:** Intermediate/Advanced · **Local cost:** $0

## Outcomes
Understand how Terraform/OpenTofu resolve providers, authenticate to registries, verify checksums, and install plugins; configure safe plugin caches and approved filesystem/network mirrors; troubleshoot TLS, DNS, proxies, registry outages and architecture mismatch; execute reproducible labs and automated policy tests.

## 1. Provider installation architecture
```text
Git root module + required_providers + .terraform.lock.hcl
                     |
               terraform init
                     |
         provider source resolution
                     |
         registry discovery / mirror rules
                     |
        version constraint + lock selection
                     |
        checksum / platform verification
                     |
     per-working-directory .terraform/ plugins
                     |
              plan / apply runtime
```
A provider **source address** (e.g. `registry.terraform.io/hashicorp/random`) identifies a namespace and registry; a **version constraint** expresses allowed versions; `.terraform.lock.hcl` records selected versions and checksums. Terraform/OpenTofu CLI versions and reusable module revisions are managed separately. Never manually fabricate lockfile hashes.

### Three installation locations
1. **Working directory:** `.terraform/` is transient installation metadata, excluded from Git.
2. **Shared plugin cache:** `TF_PLUGIN_CACHE_DIR` can reduce repeated downloads; directory must exist and be writable. Cache is not an authoritative lockfile or secure provider mirror.
3. **Provider installation mirror:** explicit `provider_installation` configuration in CLI configuration can restrict installation to a controlled filesystem or network mirror. Trust and checksum verification remain essential.

**Critical:** do not share a writable plugin cache between untrusted users or concurrently write to the same cache without validated locking behavior. Provider installation settings belong in the CLI configuration, not in `main.tf`.

## 2. Registry and trust boundaries
Provider discovery normally contacts the public or configured registry to discover available versions and package metadata. Enterprises may use approved mirrors, internal registries, proxy allowlists and artifact attestations. Ensure the correct registry hostname, provider namespace, platform package and checksum. A provider binary is executable code: malicious or tampered packages can compromise the runner and cloud credentials.

### Provider version selection
```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
```
This is a **networked optional example**. `terraform init` downloads `hashicorp/random` and writes `.terraform.lock.hcl`. Subsequent `terraform init -lockfile=readonly` should reuse approved selections; `terraform init -upgrade` may select a newer allowed version and requires review. The exact provider version available changes over time.

## 3. Environment setup
Use approved Terraform or OpenTofu, Python 3.9+, Git, and optional curl/openssl. Linux/WSL2:
```bash
terraform version
python3 --version
git --version
mkdir -p "$HOME/.terraform.d/plugin-cache"
export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"
```
For PowerShell:
```powershell
New-Item -ItemType Directory -Force "$HOME/.terraform.d/plugin-cache" | Out-Null
$env:TF_PLUGIN_CACHE_DIR = "$HOME/.terraform.d/plugin-cache"
terraform version
```
OpenTofu users substitute `tofu` for `terraform` and verify support for the same environment setting in their approved version. Avoid exposing proxy passwords or registry tokens in terminal transcripts. CLI configuration locations differ by tool and OS; consult vendor documentation.

## 4. Lab A — Offline built-in provider smoke test
The supplied `labs/chapter-009/offline/main.tf` uses built-in `terraform_data`; no external provider is downloaded. It verifies CLI initialization and state lifecycle but **does not validate registry or plugin-cache downloads**.
```bash
cd infrastructure-as-code/labs/chapter-009/offline
terraform init
terraform fmt -check
terraform validate
terraform plan -out=offline.tfplan
terraform apply offline.tfplan
terraform output -json
terraform plan -detailed-exitcode
terraform destroy
terraform state list
```
Expected: one local resource, no changes on second plan (exit 0), and empty state list after destroy. Replace `terraform` with `tofu` consistently if using OpenTofu.

## 5. Lab B — Online provider download and plugin cache
Requires internet or an approved registry mirror. From `labs/chapter-009/online`:
```bash
terraform init
terraform providers
terraform providers lock -platform=linux_amd64 -platform=windows_amd64
terraform init -lockfile=readonly
terraform validate
terraform plan
```
The `online/main.tf` uses `hashicorp/random` and a `random_pet` resource, with no cloud credentials. Observe `.terraform.lock.hcl` and the cache directory. Commit the reviewed lockfile for this root if you choose to track the online lab; never commit `.terraform/`, `*.tfstate`, or plan files. Multi-platform lock generation needs registry or mirror access. Clean up with `terraform destroy` and verify state.

**Cache validation:** copy the online root into a new disposable directory, keeping its reviewed lockfile, and rerun `init`. Compare logs/timing; cache hits depend on the selected version, architecture, platform and mirror configuration. Do not claim a cache hit solely because `TF_PLUGIN_CACHE_DIR` is set.

## 6. Lab C — Filesystem mirror configuration (advanced)
The example `terraformrc.example` illustrates provider installation routing. **Do not enable it until the mirror contains legitimate, checksum-verified packages for the intended platform.** Copy it to a disposable CLI configuration and adjust the absolute mirror path. `direct { exclude = [...] }` is used to prevent fallback for mirrored providers; test in a nonproduction environment. A mirror that is empty should cause `init` to fail closed rather than downloading an unapproved binary.

```hcl
provider_installation {
  filesystem_mirror {
    path    = "/opt/company/terraform-providers"
    include = ["registry.terraform.io/hashicorp/*"]
  }
  direct {
    exclude = ["registry.terraform.io/hashicorp/*"]
  }
}
```
On Linux, use `TF_CLI_CONFIG_FILE` to point to the reviewed configuration. On Windows, adapt paths to Windows syntax. Provider mirror directory structure must follow the vendor's documented packed/unpacked layout; copying an arbitrary binary into a directory is insufficient. Use `terraform providers mirror <directory>` from an online, approved environment to create a proper mirror for configured providers.

## 7. Lab D — Automated registry policy and tests
`registry-policy.json` is a fictional policy inventory. `validate_registry.py` validates source addresses, explicit version constraints, lockfile requirement, checksum verification, allowed registries, and cache/mirror trust rules. It is a **teaching validator**, not a real binary attestation or Terraform lockfile parser.
```bash
cd infrastructure-as-code/labs/chapter-009
python3 validate_registry.py registry-policy.json
python3 -m unittest -v test_validate_registry.py
```
Expected: PASS and all tests pass. Negative drills: duplicate provider source, set `verify_checksums=false`, enable an untrusted mirror, or remove `lockfile_committed`; each must fail with exit 1. Run negative drills on copies, not the committed policy.

## 8. Lab E — Read-only network diagnostics
Run the stdlib-only diagnostic helper against an approved public or internal registry:
```bash
python3 network_diagnostics.py registry.terraform.io
python3 -m unittest -v test_network_diagnostics.py
```
The helper resolves DNS and attempts a TLS connection on port 443, reporting protocol/certificate status without transmitting credentials. It does not install providers or bypass TLS verification. Corporate proxies can prevent direct TLS checks; report the limitation rather than disabling validation. Network results are environment-dependent and may fail in an offline lab.

## 9. Production SRE/DBRE scenarios
**A — AWS EKS pipeline blocked by registry outage:** Existing approved provider cache may allow a reproducible build, but only if platform, lockfile and plugin selection match. Use an approved mirror; do not bypass checksum verification.

**B — Azure AKS WSL vs Windows mismatch:** Provider package downloaded for Windows cannot run inside Linux WSL2. Verify `terraform version`, `uname -m`, platform checksums and CLI path.

**C — RDS provider upgrade proposes replacement:** Freeze production apply. Review provider diff, state schema, backup/PITR and DBRE-approved migration/rollback plan. A successful `init` does not imply safe `apply`.

**D — Elasticsearch storage incident:** A provider update changes disk configuration behavior while manual emergency IOPS adjustments exist. Preserve incident mitigation and reconcile code only after SLO recovery.

**E — CI proxy intercepts TLS:** Investigate corporate CA trust, proxy variables, DNS and allowlists. Install organization-approved CA; never use insecure TLS flags or ignore checksum mismatch.

**F — Poisoned shared plugin cache:** Quarantine cache, revoke affected runner credentials if compromise is suspected, rebuild from verified artifacts and audit supply-chain exposure.

**G — Multi-cloud DR with disconnected network:** Test offline mirror, state/backend access, provider packages, credentials and encryption keys before declaring DR readiness.

## 10. Troubleshooting decision table
| Error | Likely cause | Safe response |
|---|---|---|
| Failed to query provider packages | DNS/proxy/registry outage | Verify DNS/TLS and approved mirror |
| x509 certificate signed by unknown authority | Missing corporate CA or interception | Install trusted CA; no insecure bypass |
| Provider checksum mismatch | Corruption/platform/tampering | Stop, quarantine, verify hashes |
| No available releases match constraints | Overly narrow constraint or lock | Review constraint and upgrade plan |
| Failed to install provider | Cache permission/disk | Fix ownership/capacity; retry |
| Provider binary exec format error | Wrong OS/CPU architecture | Download correct platform package |
| `-lockfile=readonly` fails | Lockfile out of sync | Controlled regeneration and PR |
| Mirror provider not found | Wrong layout or absent version | Rebuild mirror using approved command |
| Proxy timeout | Routing/firewall/proxy | Check approved proxy and allowlists |
| Unexpected resource replacement | Provider schema or config drift | Stop, owner/DBRE review |

## 11. Operational runbooks
**New provider onboarding:** approve source/publisher → define version constraint → initialize in sandbox → review lockfile and checksums → test supported platforms → register mirror/cache → run security review → stage rollout → approve prod.

**Registry outage:** confirm incident scope → check DNS/proxy/TLS → assess cache/mirror availability → preserve lockfile → use verified mirror → record recovery evidence → do not force upgrade.

**Checksum/security incident:** halt CI applies → quarantine package/cache → validate upstream signatures/checksums → rotate exposed credentials as needed → rebuild runners → document RCA/COA.

**Unexpected plan after provider update:** compare CLI/provider/module versions and backend identity → inspect lockfile diff → confirm state integrity → assess destructive actions → replan under approval.

## 12. Security and FinOps
Pin versions and immutable CI images, commit reviewed lockfiles, isolate cache write permissions, verify checksums, maintain approved mirrors, monitor registry dependencies, and retain audit logs. A mirror improves availability but adds storage, patching and provenance responsibilities. Never log tokens, proxy credentials or sensitive plan/state data.

## 13. Acceptance
- [ ] Offline `terraform_data` lab validates and cleans up
- [ ] Online provider lab installs verified package and generates real lockfile
- [ ] Readonly lockfile initialization succeeds
- [ ] Cache/mirror behavior tested without weakening trust
- [ ] Python registry policy tests pass; negative cases fail closed
- [ ] DNS/TLS diagnostics run or offline limitation documented
- [ ] No credentials, plan, state or `.terraform/` committed
- [ ] SRE owner and incident recovery procedure identified

## 14. Knowledge check
What is the difference between a plugin cache and mirror? Does `.terraform.lock.hcl` pin CLI version? What does `init -upgrade` change? Why do platform checksums matter? What should happen when a mirror lacks a package? How do you diagnose TLS interception safely? Why is an RDS replacement risk independent of successful provider installation?

**Next:** Chapter 010 — IaC Development Tooling Integration, CI Preflight and Environment Readiness Capstone.
