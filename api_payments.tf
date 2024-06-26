# /payments

module "payments" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "payments"
}

# /payments/membership
module "payments_membership" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.payments.resource_id
  path_part   = "membership"
}

# /payments/membership/{session}
module "payments_membership_session" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.payments_membership.resource_id
  path_part   = "{session}"
}

module "payments_membership_session_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.payments_membership_session.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "payments_membership_session"
  description = "Handle successful payment"

  lambda_path = "${path.module}/lambda/api/payments/membership/{session}/GET"

  lambda_policy = {
    dynamodb_get = {
      actions   = ["dynamodb:GetItem"]
      resources = [aws_dynamodb_table.members_table.arn]
      condition = {
        forallvalues_condition = {
          test     = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values   = ["membershipNumber", "membershipExpires"]
        }
        stringequals_condition = {
          test     = "StringEquals"
          variable = "dynamodb:Select"
          values   = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }

    dynamodb_update = {
      actions   = ["dynamodb:UpdateItem"]
      resources = [aws_dynamodb_table.members_table.arn]
      condition = {
        forallvalues_condition = {
          test     = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values   = ["membershipNumber", "membershipExpires", "status"]
        }
        stringequals_condition = {
          test     = "StringEquals"
          variable = "dynamodb:ReturnValues"
          values   = ["NONE", "UPDATED_OLD", "UPDATED_NEW"]
        }
      }
    }

    secrets = {
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [aws_secretsmanager_secret.api_keys.arn]
    }
  }

  lambda_env = {
    API_KEY_SECRET_NAME = aws_secretsmanager_secret.api_keys.arn
    MEMBERS_TABLE       = aws_dynamodb_table.members_table.id
    PORTAL_DOMAIN       = aws_route53_record.portal.fqdn
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}