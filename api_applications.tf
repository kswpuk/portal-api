# /applications

module "applications" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "applications"
}

module "applications_GET" {
  source = "./api_method_dynamodb"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "applications"
  
  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "Scan"
  dynamodb_table_arn = aws_dynamodb_table.applications_table.arn

  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.applications_table.name}"
}
END

  response_template = local.dynamodb_to_array_vtl
}

# /applications/{id}

module "applications_id" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications.resource_id
  path_part   = "{id}"
}

module "applications_id_GET" {
  source = "./api_method_dynamodb"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "applications_id"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "Query"
  dynamodb_table_arn = aws_dynamodb_table.applications_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.applications_table.name}",
  "KeyConditionExpression": "membershipNumber = :v",
  "ExpressionAttributeValues": {
    ":v": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    }
  }
}
END

  response_template = local.dynamodb_to_item_vtl
}

# /applications/{id}/references

module "applications_id_references" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id.resource_id
  path_part   = "references"
}

module "applications_id_references_GET" {
  source = "./api_method_dynamodb"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_references.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "applications_id_references"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "Query"
  dynamodb_table_arn = aws_dynamodb_table.references_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.references_table.name}",
  "KeyConditionExpression": "membershipNumber = :v",
  "ExpressionAttributeValues": {
    ":v": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    }
  }
}
END

  response_template = local.dynamodb_to_array_vtl
}
