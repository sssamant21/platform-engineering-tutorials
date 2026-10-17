# Azure authentication review checklist

Use approved managed identity or workload identity federation. Verify the tenant ID, subscription ID, principal object ID, role assignments, scope and remote backend identity separately. Do not paste access tokens, client secrets or subscription-specific credentials into Git. Run az account show and inspect the selected subscription before any Terraform plan; verify the effective principal through approved cloud audit tooling. A login alone is not sufficient proof of the intended target. Plan and apply require independent approval.
