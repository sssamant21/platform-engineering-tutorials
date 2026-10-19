# Optional native preview reference — NOT executed

## Pulumi
- Verify `pulumi whoami`, `pulumi stack ls`, backend and provider target.
- In an approved isolated lab, run `pulumi preview --json` with read-only permissions where feasible.
- Do not run `pulumi up` or `destroy` as part of this chapter.

## CloudFormation
- Use AWS STS caller identity and verify account/region.
- Template validation: `aws cloudformation validate-template --template-body file://template.yaml`.
- A change set may create stack metadata; it is **not** strictly read-only. Create only with explicit lab authorization. Inspect `describe-change-set` before any execute.

## Bicep
- Verify `az account show` and selected tenant/subscription.
- Compile locally with `az bicep build --file main.bicep`.
- What-if requires Azure authorization and can incur API reads; review scope and RBAC first.
- Never run `az deployment ... create` as part of the offline lab.

These commands do not establish production approval or recovery readiness.
