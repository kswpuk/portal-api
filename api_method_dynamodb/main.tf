data "aws_region" "current" {}

data "aws_api_gateway_rest_api" "api" {
  name = var.rest_api_name
}

data "aws_api_gateway_resource" "resource" {
  rest_api_id = data.aws_api_gateway_rest_api.api.id
  path = var.path
}

resource "aws_api_gateway_method" "method" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = data.aws_api_gateway_resource.resource.id

  authorization = length(var.authorizer_id) > 0 ? "CUSTOM" : "NONE"
  authorizer_id = var.authorizer_id

  http_method   = var.http_method
}

resource "aws_api_gateway_integration" "integration" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = data.aws_api_gateway_resource.resource.id

  http_method             = aws_api_gateway_method.method.http_method
  integration_http_method = "POST"

  type = "AWS"
  uri  = "arn:aws:apigateway:${data.aws_region.current.name}:dynamodb:action/${var.dynamodb_action}"
  
  credentials = aws_iam_role.role.arn

  request_templates = {
    "application/json" = var.request_template
  }
}

resource "aws_api_gateway_method_response" "response200" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = data.aws_api_gateway_resource.resource.id

  http_method = aws_api_gateway_method.method.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_integration_response" "response200" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = data.aws_api_gateway_resource.resource.id

  http_method = aws_api_gateway_method.method.http_method
  status_code = aws_api_gateway_method_response.response200.status_code

  response_templates = {
    "application/json" = var.response_template
  }

  # TODO: Restrict this?
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,HEAD,POST,PUT,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [
    aws_api_gateway_integration.integration
  ]
}

resource "aws_iam_role" "role" {
  name = "${var.prefix}-${var.name}-${var.http_method}-role"
  assume_role_policy = data.aws_iam_policy_document.agw_assume_role_policy.json
}

resource "aws_iam_role_policy" "policy" {
  name = "${var.prefix}-${var.name}-${var.http_method}-policy"
  role = aws_iam_role.role.id

  policy = data.aws_iam_policy_document.policy.json
}

data "aws_iam_policy_document" "policy" {
  statement {
    actions = ["dynamodb:${var.dynamodb_action}"]
    resources = [ var.dynamodb_table_arn ]
  }
}

data "aws_iam_policy_document" "agw_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}