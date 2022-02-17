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

  request_parameters = {
    "method.request.path.${var.path_key}" = true
  }
}

resource "aws_api_gateway_integration" "integration" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = data.aws_api_gateway_resource.resource.id

  http_method             = aws_api_gateway_method.method.http_method
  integration_http_method = var.http_method

  type = "AWS"
  uri  = "arn:aws:apigateway:${data.aws_region.current.name}:s3:path/${var.s3_bucket}/${var.s3_prefix}{key}${var.s3_suffix}"
  
  credentials = aws_iam_role.role.arn

  request_parameters = {
    "integration.request.path.key" = "method.request.path.${var.path_key}"
  }
}

resource "aws_api_gateway_method_response" "response200" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = data.aws_api_gateway_resource.resource.id

  http_method = aws_api_gateway_method.method.http_method
  status_code = "200"

  response_parameters = {
    # CORS
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin" = true

    # S3
    "method.response.header.Timestamp" = true
    "method.response.header.Content-Length" = true
    "method.response.header.Content-Type" = true
  }
}

resource "aws_api_gateway_integration_response" "response200" {
  rest_api_id   = data.aws_api_gateway_rest_api.api.id
  resource_id   = data.aws_api_gateway_resource.resource.id

  http_method = aws_api_gateway_method.method.http_method
  status_code = aws_api_gateway_method_response.response200.status_code

  response_parameters = {
    # CORS - Restrict this?
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,HEAD,POST,PUT,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"

    # S3
    "method.response.header.Timestamp" = "integration.response.header.Date"
    "method.response.header.Content-Length" = "integration.response.header.Content-Length"
    "method.response.header.Content-Type" = "integration.response.header.Content-Type"
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
    # TODO: Should really lock this down further - map HTTP verb to actions?
    actions = ["s3:*"]
    resources = [ "arn:aws:s3:::${var.s3_bucket}/*" ]
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