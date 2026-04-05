
resource_group_name  = "rgp-dev-mes"
location             = "Central India"
storage_account_name = "tddevtfstate123"
function_app_name    = "func-fastapi-dev-cj"
key_vault_name       = "kvmesdev123"

# These are only used if you want Terraform to also create AKV secrets
# Since your AKV already has phost/pdb/puser/ppassword — leave these blank
db_host = ""
db_name = ""
db_user = ""
db_pass = ""