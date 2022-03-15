# /events

module "events" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "events"
}

module "events_GET" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.events.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "events"
  description = "List Events"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/GET"

  lambda_policy = {
    dynamodb = {
      actions = [ 
        "dynamodb:GetItem",
        "dynamodb:Scan"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn,
        aws_dynamodb_table.event_instance_table.arn,
        "${aws_dynamodb_table.event_instance_table.arn}/index/*",
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }
  }
  
  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE = aws_dynamodb_table.event_series_table.id
  }
}