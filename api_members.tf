# /members

module "members" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "members"
}

module "members_GET" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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
  "ProjectionExpression": "membershipNumber,firstName,preferredName,surname,#r,#s",
  "ExpressionAttributeNames": {"#r": "role", "#s": "status"}
}
END

  response_template = local.dynamodb_to_array_vtl
}

# /members/compare

module "members_compare" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "compare"
}

module "members_compare_POST" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_compare.resource_path

  http_method = "POST"

  prefix = var.prefix
  name = "members_compare"
  description = "Compare membership list to Compass"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/compare/POST"

  lambda_policy = {
    dynamodb = {
      actions = [ "dynamodb:Scan" ]
      resources = [ aws_dynamodb_table.members_table.arn ]
    }
  }
  
  lambda_env = {
    MEMBERS_TABLE = aws_dynamodb_table.members_table.name
  }
}

# /members/{id}

module "members_id" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "{id}"
}

module "members_id_GET" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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

# /members/{id}/allocations

module "members_id_allocations" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "allocations"
}

module "members_id_allocations_GET" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id_allocations.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "members_id_allocations"
  description = "Get allocations for member"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/allocations/GET"

  lambda_policy = {
    allocations = {
      actions = [ "dynamodb:Query" ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn,
        "${aws_dynamodb_table.event_allocation_table.arn}/index/${var.prefix}-member_event_allocations"
      ]
    }

    event_series = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.event_series_table.arn ]
    }

    event_instance = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.event_instance_table.arn ]
    }

    members = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.members_table.arn ]
    }
  }
  
  lambda_env = {
    EVENT_ALLOCATIONS_INDEX = "${var.prefix}-member_event_allocations"
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE = aws_dynamodb_table.event_series_table.id
    MEMBERS_TABLE = aws_dynamodb_table.members_table.id
  }
}

# /members/{id}/necker

module "members_id_necker" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "necker"
}

module "members_id_necker_PATCH" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id_necker.resource_path

  http_method   = "PATCH"

  prefix = var.prefix
  name = "members_id_necker"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "UpdateItem"
  dynamodb_table_arn = aws_dynamodb_table.members_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.members_table.name}",
  "Key": {
    "membershipNumber": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    }
  },
  "UpdateExpression": "SET receivedNecker = :v",
  "ExpressionAttributeValues": {
    ":v": {
      "BOOL": #if( $input.json('$.receivedNecker') == false ) false #else true #end
    }
  }
}
END
}

# /members/{id}/payment

module "members_id_payment" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "payment"
}

module "members_id_payment_POST" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "photo"
}

module "members_id_photo_GET" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id_photo.resource_path

  http_method = "GET"

  prefix = var.prefix
  name = "members_id_photo"
  description = "Get member photo"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/photo/GET"

  lambda_policy = {
    s3 = {
      actions = [ "s3:GetObject" ]
      resources = [ "${aws_s3_bucket.member_photos_bucket.arn}/*.jpg" ]
    }

    s3_bucket = {
      actions = [ "s3:ListBucket" ]
      resources = [ aws_s3_bucket.member_photos_bucket.arn ]
    }
  }
  
  lambda_env = {
    EXPIRATION = 3600
    PHOTO_BUCKET_NAME = aws_s3_bucket.member_photos_bucket.id
  }
}

module "members_id_photo_PUT" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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

# /members/{id}/role

module "members_id_role" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "role"
}

module "members_id_role_PATCH" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.members_id_role.resource_path

  http_method   = "PATCH"

  prefix = var.prefix
  name = "members_id_role"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "UpdateItem"
  dynamodb_table_arn = aws_dynamodb_table.members_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.members_table.name}",
  "Key": {
    "membershipNumber": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    }
  },
  "UpdateExpression": "SET #k = :v",
  "ExpressionAttributeNames": {
    "#k": "role"
  }
  "ExpressionAttributeValues": {
    ":v": {
      "S": $input.json('$.role') == false )
    }
  }
}
END
}