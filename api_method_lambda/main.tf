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

  type = "AWS_PROXY"
  uri  = module.lambda.lambda_function_invoke_arn
}

module "lambda" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = var.lambda_path
      pip_requirements = fileexists("${var.lambda_path}/requirements.txt")
    }
  ]

  function_name = "${var.prefix}-${var.name}-${var.http_method}-lambda"
  description = var.description
  handler = var.lambda_handler
  runtime = var.lambda_runtime

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = length(var.lambda_policy) > 0
  policy_statements = var.lambda_policy

  role_name = "${var.prefix}-${var.name}-${var.http_method}-role"

  publish = true
  allowed_triggers = {
    api_gateway = {
      service    = "apigateway"
      source_arn = "${data.aws_api_gateway_rest_api.api.execution_arn}/*/${aws_api_gateway_method.method.http_method == "ANY" ? "*" : aws_api_gateway_method.method.http_method}${var.path}"
    }
  }

  timeout = var.lambda_timeout
  memory_size = var.lambda_memory

  environment_variables = var.lambda_env
}