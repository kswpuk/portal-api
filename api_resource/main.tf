resource "aws_api_gateway_resource" "res" {
  rest_api_id = var.rest_api_id
  parent_id   = var.parent_id
  path_part   = var.path_part
}

module "cors" {
  source  = "mewa/apigateway-cors/aws"
  version = "2.0.1"

  api      = var.rest_api_id
  resource = aws_api_gateway_resource.res.id

  methods = ["GET", "HEAD", "POST", "PUT", "PATCH"]
}