# IaC Tutorial Status

**Progress:** 24 / 120 chapters (20.00%)  
**Last update:** 2026-10-17  
**Chapter 001:** Published; local lab execution remains for learner verification.  
**Chapter 002:** Published; live lab execution remains for learner verification.  
**Chapter 003:** Published; live lab execution remains for learner verification.  
**Chapter 004:** Published; live lab execution remains for learner verification.  
**Chapter 005:** Published; live lab execution remains for learner verification.  
**Part 01:** 5/5 chapters published (labs not independently executed).  
**Chapter 006:** Published; live lab execution remains for learner verification.  
**Part 02:** 5/5 chapters published (live lab evidence pending).  
**Chapter 007:** Published; live lab execution remains for learner verification.  
**Chapter 008:** Published; live lab execution remains for learner verification.  
**Chapter 009:** Published; live lab execution remains for learner verification.  
**Chapter 010:** Published; live lab execution remains for learner verification.  
**Chapter 011:** Published; live lab execution remains for learner verification.  
**Part 03:** 5/5 chapters published (live lab evidence pending).  
**Chapter 012:** Published; live lab execution remains for learner verification.  
**Chapter 013:** Published; live lab execution remains for learner verification.  
**Chapter 014:** Published; live lab execution remains for learner verification.  
**Chapter 015:** Published; Part 03 content complete; live lab execution remains for learner verification.  
**Chapter 016:** Published; live lab execution remains for learner verification.  
**Part 04:** 5/5 chapters published (live lab evidence pending).  
**Chapter 017:** Published; live lab execution remains for learner verification.  
**Chapter 018:** Published; live lab execution remains for learner verification.  
**Chapter 019:** Published; live lab execution remains for learner verification.  
**Chapter 020:** Published; Part 04 content complete; live lab execution remains for learner verification.  
**Chapter 021:** Published; live lab evidence pending.  
**Part 05:** 4/5 chapters published.  
**Chapter 022:** Published; live lab evidence pending.  
**Chapter 023:** Published; live lab evidence pending.  
**Chapter 024:** Published; live lab evidence pending.  
**Next:** Chapter 025 — Terraform Providers, Dependencies and Lifecycle Production Capstone.

| Chapter | Title | Status |
|---|---|---|
| 001 | IaC Fundamentals, Architecture and Enterprise Use Cases | Published |
| 002 | IaC Tooling Landscape and Selection Criteria | Published |
| 003 | Declarative vs Imperative IaC, Desired State, Drift and Idempotence | Published |
| 004 | IaC Lifecycle, Version Control, Git Workflows and Change Management | Published |
| 005 | Enterprise IaC Architecture, Operating Models and Governance | Published |
| 006 | IaC Workstation Setup, CLI Installation and Toolchain Validation | Published |
| 007 | IaC Repository Structure, Environment Isolation and Workspace Standards | Published |
| 008 | Terraform and OpenTofu Version Management, Provider Lockfiles and Reproducible Toolchains | Published |
| 009 | Provider Installation, Plugin Caching, Registries and Network Troubleshooting | Published |
| 010 | IaC Development Tooling Integration, CI Preflight and Environment Readiness Capstone | Published |
| 011 | Terraform Configuration Language Fundamentals: Blocks, Arguments, Expressions and HCL Syntax | Published |
| 012 | Terraform Resource Blocks, Data Sources, Meta-Arguments and Dependency Graph | Published |
| 013 | Terraform Plan, Apply, Refresh, Destroy and Execution Lifecycle | Published |
| 014 | Terraform State Inspection, Drift Detection and Resource Address Management | Published |
| 015 | Terraform Language, Lifecycle, State and Change Management Capstone | Published |
| 016 | Terraform Input Variables, Type Constraints, Defaults and Validation | Published |
| 017 | Terraform Local Values, Expressions, Functions and Dynamic Configuration | Published |
| 018 | Terraform Collections, for Expressions, Splat Expressions and Advanced Data Transformations | Published |
| 019 | Terraform Conditional Expressions, Null Handling, try/can and Defensive Configuration Patterns | Published |
| 020 | Terraform Variables, Expressions and Defensive Configuration Production Capstone | Published |
| 021 | Terraform Provider Configuration, Aliases, Version Constraints and Authentication | Published |
| 022 | Terraform Provider Dependencies, Implicit and Explicit Resource Graphs and Lifecycle Ordering | Published |
| 023 | Terraform Data Sources, External Dependencies and Cross-Module Data Flow | Published |
| 024 | Terraform Lifecycle Meta-Arguments, Preconditions, Postconditions and Safe Replacement Strategies | Published |

## Chapter 001 acceptance
- [x] Theory, architecture, executable lab files
- [x] Validation criteria and expected results
- [x] SRE/DBRE scenarios, runbooks, security and cleanup
- [ ] Live lab execution evidence

## Chapter 002 acceptance
- [x] Architecture and tool comparisons
- [x] Terraform/OpenTofu and Ansible lab files
- [x] Python scorecard and unit tests
- [x] SRE/DBRE scenarios, troubleshooting and recovery runbooks
- [ ] Live lab execution evidence

## Chapter 003 acceptance
- [x] Declarative/imperative theory and architecture
- [x] Terraform/OpenTofu and Ansible hands-on labs
- [x] Python drift detector and unit tests
- [x] Production SRE/DBRE scenarios and troubleshooting
- [x] Runbooks, security and cleanup instructions
- [ ] Live lab execution evidence

## Chapter 004 acceptance
- [x] Lifecycle, Git workflows, plan/apply approval theory
- [x] Terraform and change-policy labs
- [x] Python automated policy tests
- [x] SRE/DBRE production cases, troubleshooting, runbooks
- [ ] Live lab execution evidence

## Chapter 005 acceptance
- [x] Enterprise architecture, ownership and operating models
- [x] Terraform governance metadata lab
- [x] Python governance inventory and unit tests
- [x] SRE/DBRE cases, security controls, troubleshooting and runbooks
- [x] Part 01 final assessment
- [ ] Live lab execution evidence

## Chapter 006 acceptance
- [x] Windows/WSL2 and Linux workstation setup instructions
- [x] Terraform/OpenTofu, Git, VS Code, Python toolchain guidance
- [x] Executable no-cloud IaC smoke test
- [x] Automated Python workstation audit and unit tests
- [x] SRE/DBRE production cases, troubleshooting and runbooks
- [ ] Live lab execution evidence

## Chapter 007 acceptance
- [x] Repository architecture and workspace isolation theory
- [x] Reusable Terraform module and separate dev/staging roots
- [x] Disposable workspace demonstration
- [x] Python stack inventory validator and unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [ ] Live lab execution evidence

## Chapter 008 acceptance
- [x] CLI/provider/module/state compatibility and lockfile theory
- [x] Executable local Terraform/OpenTofu smoke test
- [x] Python manifest policy, CLI drift check and automated unit tests
- [x] Optional provider lockfile and upgrade workflow
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [ ] Live lab execution evidence

## Chapter 009 acceptance
- [x] Provider installation, registry, cache and mirror theory
- [x] Offline and online Terraform/OpenTofu lab configurations
- [x] Example controlled provider mirror CLI configuration
- [x] Python registry policy validator and automated tests
- [x] DNS/TLS diagnostic helper and automated tests
- [x] Production SRE/DBRE cases, troubleshooting and runbooks
- [ ] Live lab execution evidence

## Chapter 010 acceptance
- [x] Integrated developer-to-CI preflight architecture and change gates
- [x] No-cloud Terraform/OpenTofu smoke test
- [x] Python readiness policy, artifact hygiene and automated unit tests
- [x] Shell preflight and sample GitHub Actions workflow
- [x] Production SRE/DBRE scenarios, troubleshooting, security and runbooks
- [x] Part 02 final readiness assessment
- [ ] Live lab execution evidence

## Chapter 011 acceptance
- [x] HCL blocks, arguments, expressions, types and dependency theory
- [x] Typed variable validation and built-in Terraform/OpenTofu local lab
- [x] Terraform console, negative tests and cleanup exercises
- [x] Python HCL source-policy checks and automated unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [ ] Live lab execution evidence

## Chapter 012 acceptance
- [x] Resource/data source, meta-argument and graph architecture
- [x] Built-in Terraform/OpenTofu graph lab with stable for_each keys
- [x] Lifecycle prevent_destroy failure injection and cleanup procedure
- [x] Python graph inventory policy and seven automated unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [ ] Live lab execution evidence

## Chapter 013 acceptance
- [x] Plan/apply/refresh-only/destroy lifecycle theory and architecture
- [x] No-cloud Terraform/OpenTofu lab, saved plans and drift exercises
- [x] Python plan JSON policy, synthetic sample plan and ten unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting and operational runbooks
- [x] Pre-apply shell workflow and safe cleanup instructions
- [ ] Live lab execution evidence

## Chapter 014 acceptance
- [x] State architecture, drift taxonomy, resource address and migration theory
- [x] Local Terraform/OpenTofu lab with state inspection and refresh-only exercise
- [x] Read-only state JSON inventory validator and ten automated unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [x] Safe cleanup and state artifact hygiene
- [ ] Live lab execution evidence

## Chapter 015 acceptance
- [x] Integrated Part 03 HCL, dependency graph, lifecycle and state capstone
- [x] No-cloud Terraform/OpenTofu project, saved plans and address migration lab
- [x] Change-ticket/plan policy and eleven automated unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting, runbooks and 100-point rubric
- [x] Part 03 curriculum publication complete (011–015)
- [ ] Live lab execution evidence and final assessment results

## Chapter 016 acceptance
- [x] Terraform variable types, defaults, nullability, sensitivity and precedence theory
- [x] Local Terraform/OpenTofu typed-input lab and dev/prod example tfvars
- [x] Python environment input-policy and eleven automated unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [x] Chapter and GitHub index publication
- [ ] Live lab execution evidence

## Chapter 017 acceptance
- [x] Locals, expressions, functions, for_each and dynamic block theory
- [x] No-cloud Terraform/OpenTofu lab with dev/prod example tfvars
- [x] Python expression policy and twelve automated unit tests
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [x] GitHub chapter and master index publication
- [ ] Live lab execution evidence

## Chapter 018 acceptance
- [x] Collections, for/splat expressions, grouping and data transformation theory
- [x] No-cloud Terraform/OpenTofu service×zone matrix lab with dev/prod inputs
- [x] Python transformation policy and fifteen automated unit tests authored
- [x] Production SRE/DBRE scenarios, troubleshooting and operational runbooks
- [x] GitHub chapter and master index publication
- [ ] Live Terraform execution and unit-test evidence

## Chapter 019 acceptance
- [x] Conditional expressions, null/unknown values, try/can and fail-closed configuration theory
- [x] No-cloud Terraform/OpenTofu lab with dev/prod inputs and lifecycle preconditions
- [x] Python defensive configuration policy and sixteen automated unit tests authored
- [x] Production SRE/DBRE scenarios, troubleshooting and operational runbooks
- [x] GitHub chapter and master index publication
- [ ] Live Terraform execution and unit-test evidence

## Chapter 020 acceptance
- [x] Integrated Part 04 typed variables, locals, expressions, transformations and defensive configuration
- [x] No-cloud Terraform/OpenTofu capstone with dev/prod inputs and lifecycle preconditions
- [x] Input/plan policy and twenty-two automated unit tests authored
- [x] Production SRE/DBRE scenarios, troubleshooting, runbooks and 100-point rubric
- [x] Part 04 curriculum publication complete (016–020)
- [ ] Live Terraform execution, unit-test evidence and final assessment results

## Chapter 021 acceptance
- [x] Provider source, version constraints, aliases, lockfile and identity theory
- [x] Offline terraform_data lab with AWS alias and Azure/GCP auth examples
- [x] Provider manifest policy and sixteen automated unit tests authored
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [x] Chapter and master index publication
- [ ] Live lab execution and test evidence

## Chapter 022 acceptance
- [x] Implicit/explicit dependencies, DAG, data reads, provider and lifecycle theory
- [x] Offline terraform_data graph lab and sample plan JSON
- [x] Python graph and plan policy with seventeen automated unit tests authored
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [x] Chapter and master index publication
- [ ] Live lab execution and test evidence

## Chapter 023 acceptance
- [x] Data sources, read timing, cross-module output contracts and sensitive state theory
- [x] Offline network/database Terraform module lab and dev/prod fixtures
- [x] Python contract policy and twenty automated unit tests authored
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [x] Chapter and master index publication
- [ ] Live lab execution and test evidence

## Chapter 024 acceptance
- [x] Lifecycle meta-arguments, pre/postconditions, replacement and drift theory
- [x] Offline terraform_data lifecycle lab with dev/prod fixtures
- [x] Python lifecycle policy and eighteen automated unit tests authored
- [x] Production SRE/DBRE scenarios, troubleshooting and runbooks
- [x] Chapter and master index publication
- [ ] Live lab execution and test evidence
