# /members

module "members" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "members"
}

module "members_GET" {
  source = "./api_method_dynamodb"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "members"
  
  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "Scan"
  dynamodb_table_arn = aws_dynamodb_table.members_table.arn

  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.members_table.name}",
  "ProjectionExpression": "membershipNumber,firstName,surname,#r,#s",
  "ExpressionAttributeNames": {"#r": "role", "#s": "status"}
}
END

  response_template = <<END
#set($inputRoot = $input.path('$'))
[
#foreach($item in $inputRoot.Items) {
  #foreach($key in $item.keySet())
    "$key": "$item.get($key).S" #if($foreach.hasNext),#end
  #end
} #if($foreach.hasNext),#end
#end
]
END
}

# /members/{id}

module "members_id" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "{id}"
}

module "members_id_GET" {
  source = "./api_method_dynamodb"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "members_id"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "Query"
  dynamodb_table_arn = aws_dynamodb_table.members_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.members_table.name}",
  "KeyConditionExpression": "membershipNumber = :v",
  "ExpressionAttributeValues": {
    ":v": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    }
  }
}
END

  response_template = <<END
#set($item = $input.path('$.Items[0]'))
{
  #foreach($key in $item.keySet())
    "$key": "$item.get($key).S" #if($foreach.hasNext),#end
  #end
}
END
}

module "members_id_DELETE" {
  source = "./api_method_dynamodb"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id.resource_path

  http_method   = "DELETE"

  prefix = var.prefix
  name = "members_id"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "DeleteItem"
  dynamodb_table_arn = aws_dynamodb_table.members_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.members_table.name}",
  "Key": {
    "membershipNumber": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    }
  }
}
END 
}

module "members_id_PUT" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id.resource_path

  http_method   = "PUT"

  prefix = var.prefix
  name = "members_id"
  description = "Update Member"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/PUT"

  lambda_policy = {
    dynamodb = {
      actions = [ "dynamodb:UpdateItem" ]
      resources = [ aws_dynamodb_table.members_table.arn ]
    }
  }
  
  lambda_env = {
    TABLE_NAME = aws_dynamodb_table.members_table.id
  }
}

# /members/{id}/photo

module "members_id_photo" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "photo"
}

module "members_id_photo_GET" {
  source = "./api_method_s3"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id_photo.resource_path

  http_method = "GET"

  prefix = var.prefix
  name = "members_id_photo"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  s3_bucket = aws_s3_bucket.member_photos_bucket.id
  s3_suffix = ".jpg"
}