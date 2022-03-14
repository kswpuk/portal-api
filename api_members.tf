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

  response_template = local.dynamodb_to_array_vtl
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

  response_template = local.dynamodb_to_item_vtl
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

# /members/{id}/payment

module "members_id_payment" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "payment"
}

module "members_id_payment_POST" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id_payment.resource_path

  http_method   = "POST"

  prefix = var.prefix
  name = "members_id_payment"
  description = "Pay membership"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/payment/POST"

  lambda_policy = {
    dynamodb = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.members_table.arn ]
    }

    secrets = {
      actions = [ "secretsmanager:GetSecretValue" ]
      resources = [ aws_secretsmanager_secret.api_keys.arn ]
    }
  }
  
  lambda_env = {
    API_KEY_SECRET_NAME = aws_secretsmanager_secret.api_keys.arn
    MEMBERS_TABLE = aws_dynamodb_table.members_table.id
    PORTAL_DOMAIN = aws_route53_record.portal.fqdn

    # We have to build this manually to avoid a dependency cycle
    SUCCESS_URL = "https://${aws_api_gateway_rest_api.portal.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.prefix}/payments/membership/{CHECKOUT_SESSION_ID}"
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

module "members_id_photo_PUT" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id_photo.resource_path

  http_method   = "PUT"

  prefix = var.prefix
  name = "members_id_photo"
  description = "Update Photo"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/photo/PUT"

  lambda_policy = {
    s3 = {
      actions = [ "s3:PutObject", "s3:DeleteObject" ]
      resources = [ "${aws_s3_bucket.member_photos_bucket.arn}/*.jpg" ]
    }
  }
  
  lambda_env = {
    PHOTO_BUCKET_NAME = aws_s3_bucket.member_photos_bucket.id
  }
}