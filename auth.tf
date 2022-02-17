# Lambda
module "auth_lambda" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = "lambda/auth"
      pip_requirements = true
    }
  ]

  function_name = "${var.prefix}-auth"
  description = "Lambda Authorizer for API Gateway"
  handler = "auth.handler"
  runtime = "python3.9"

  attach_cloudwatch_logs_policy = true
  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [ "dynamodb:BatchGetItem" ]
      resources = [ aws_dynamodb_table.auth_table.arn ]
    }
  }
  assume_role_policy_statements = local.lambda_assume_role_policy

  environment_variables = {
    TABLE_NAME = aws_dynamodb_table.auth_table.id
    COGNITO_USER_POOL_ID = aws_cognito_user_pool.portal.id
    COGNITO_APP_CLIENT_ID = aws_cognito_user_pool_client.portal.id
  }
}

# Cognito
resource "aws_cognito_user_pool" "portal" {
  name = "${var.prefix}-userpool"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  mfa_configuration = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  password_policy {
    minimum_length = 8
    require_lowercase = true
    require_uppercase = true
    require_numbers = false
    require_symbols = false
  }
}

resource "aws_cognito_user_pool_client" "portal" {
  name = "${var.prefix}-client"

  user_pool_id = aws_cognito_user_pool.portal.id
  explicit_auth_flows = ["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]
}

# Cognito Groups

resource "aws_cognito_user_group" "manager" {
  name         = "MANAGER"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "QSWP Manager"
  precedence   = 1
}

resource "aws_cognito_user_group" "members" {
  name         = "MEMBERS"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "QSWP Membership Coordinator"
  precedence   = 5
}

resource "aws_cognito_user_group" "events" {
  name         = "EVENTS"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "QSWP Event Coordinator"
  precedence   = 5
}

resource "aws_cognito_user_group" "money" {
  name         = "MONEY"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "QSWP Finance Coordinator"
  precedence   = 5
}

resource "aws_cognito_user_group" "socials" {
  name         = "SOCIALS"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "QSWP Social Coordinator"
  precedence   = 10
}

resource "aws_cognito_user_group" "media" {
  name         = "MEDIA"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "QSWP Media Coordinator"
  precedence   = 10
}

resource "aws_cognito_user_group" "committee" {
  name         = "COMMITTEE"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "QSWP Committee members"
  precedence   = 20
}

resource "aws_cognito_user_group" "standard" {
  name         = "STANDARD"
  user_pool_id = aws_cognito_user_pool.portal.id
  description  = "Standard members of the QSWP"
  precedence   = 100
}

# DynamoDB
resource "aws_dynamodb_table" "auth_table" {
  name = "${var.prefix}-auth-policies"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "group"

  attribute {
    name = "group"
    type = "S"
  }
}

resource "aws_dynamodb_table_item" "auth_policy" {
  for_each = fileset("policies", "*.json")

  table_name = aws_dynamodb_table.auth_table.id
  hash_key = aws_dynamodb_table.auth_table.hash_key

  item = <<ITEM
{
  "group": {"S": "${trimsuffix(each.value, ".json")}"},
  "policy": {"S": "${replace(replace(file("policies/${each.value}"), "\n", ""), "\"", "\\\"")}"}
}
ITEM
}