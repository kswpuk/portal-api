# /members

module "members" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "members"
}

module "members_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "members"
  description = "Get membership list"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/GET"

  lambda_policy = {
    dynamodb = {
      actions   = ["dynamodb:Scan"]
      resources = [aws_dynamodb_table.members_table.arn]
    }
  }

  lambda_env = {
    COMMITTEE_GROUP = aws_cognito_user_group.committee.name
    MEMBERS_TABLE   = aws_dynamodb_table.members_table.name
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/compare

module "members_compare" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "compare"
}

module "members_compare_POST" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_compare.resource_path

  http_method = "POST"

  prefix      = var.prefix
  name        = "members_compare"
  description = "Compare membership list to Compass"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/compare/POST"

  lambda_policy = {
    dynamodb = {
      actions   = ["dynamodb:Scan"]
      resources = [aws_dynamodb_table.members_table.arn]
    }
  }

  lambda_env = {
    MEMBERS_TABLE = aws_dynamodb_table.members_table.name
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/export

module "members_export" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "export"
}

module "members_export_POST" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_export.resource_path

  http_method = "POST"

  prefix      = var.prefix
  name        = "members_export"
  description = "Export membership list as CSV"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/export/POST"

  lambda_policy = {
    allocations = {
      actions   = ["dynamodb:Query"]
      resources = [aws_dynamodb_table.event_allocation_table.arn]
    }

    members = {
      actions = [
        "dynamodb:GetItem",
        "dynamodb:Scan"
      ]
      resources = [aws_dynamodb_table.members_table.arn]
    }
  }

  lambda_env = {
    ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.name
    FIELD_NAMES       = "membershipNumber,surname,firstName,preferredName,email,telephone,address,postcode,dateOfBirth,dietaryRequirements,medicalInformation,emergencyContactName,emergencyContactTelephone,nationality,placeOfBirth,joinDate,status,role,membershipExpires,receivedNecker,lastUpdated"
    MEMBERS_TABLE     = aws_dynamodb_table.members_table.name
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/{id}

module "members_id" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "{id}"
}

module "members_id_GET" {
  source     = "./api_method_dynamodb"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id.resource_path

  http_method = "GET"

  prefix = var.prefix
  name   = "members_id"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action    = "Query"
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
  source     = "./api_method_dynamodb"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id.resource_path

  http_method = "DELETE"

  prefix = var.prefix
  name   = "members_id"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action    = "DeleteItem"
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
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id.resource_path

  http_method = "PUT"

  prefix      = var.prefix
  name        = "members_id"
  description = "Update Member"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/PUT"

  lambda_policy = {
    dynamodb = {
      actions   = ["dynamodb:UpdateItem"]
      resources = [aws_dynamodb_table.members_table.arn]
    }
  }

  lambda_env = {
    TABLE_NAME = aws_dynamodb_table.members_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/{id}/allocations

module "members_id_allocations" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "allocations"
}

module "members_id_allocations_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id_allocations.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "members_id_allocations"
  description = "Get allocations for member"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/allocations/GET"

  lambda_policy = {
    allocations = {
      actions = ["dynamodb:Query"]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn,
        "${aws_dynamodb_table.event_allocation_table.arn}/index/${var.prefix}-member_event_allocations"
      ]
    }

    event_series = {
      actions   = ["dynamodb:GetItem"]
      resources = [aws_dynamodb_table.event_series_table.arn]
    }

    event_instance = {
      actions   = ["dynamodb:GetItem"]
      resources = [aws_dynamodb_table.event_instance_table.arn]
    }

    members = {
      actions   = ["dynamodb:GetItem"]
      resources = [aws_dynamodb_table.members_table.arn]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_INDEX = "${var.prefix}-member_event_allocations"
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE      = aws_dynamodb_table.event_series_table.id
    MEMBERS_TABLE           = aws_dynamodb_table.members_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/{id}/membershipnumber

module "members_id_membershipnumber" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "membershipnumber"
}

module "members_id_membershipnumber_POST" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id_allocations.resource_path

  http_method = "POST"

  prefix      = var.prefix
  name        = "members_id_membershipnumber"
  description = "Update membership number for member"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/membershipnumber/POST"

  lambda_policy = {
    allocations = {
      actions = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn,
        "${aws_dynamodb_table.event_allocation_table.arn}/index/${var.prefix}-member_event_allocations"
      ]
    }

    members = {
      actions   = ["dynamodb:GetItem", "dynamodb:PutItem"]
      resources = [aws_dynamodb_table.members_table.arn]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_INDEX = "${var.prefix}-member_event_allocations"
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    MEMBERS_TABLE           = aws_dynamodb_table.members_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/{id}/necker

module "members_id_necker" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "necker"
}

module "members_id_necker_PATCH" {
  source     = "./api_method_dynamodb"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id_necker.resource_path

  http_method = "PATCH"

  prefix = var.prefix
  name   = "members_id_necker"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action    = "UpdateItem"
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
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "payment"
}

module "members_id_payment_POST" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id_payment.resource_path

  http_method = "POST"

  prefix      = var.prefix
  name        = "members_id_payment"
  description = "Pay membership"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/payment/POST"

  lambda_policy = {
    dynamodb = {
      actions   = ["dynamodb:GetItem"]
      resources = [aws_dynamodb_table.members_table.arn]
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

    # We have to build this manually to avoid a dependency cycle
    SUCCESS_URL = "https://${aws_api_gateway_rest_api.portal.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.prefix}/payments/membership/{CHECKOUT_SESSION_ID}"
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/{id}/photo

module "members_id_photo" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "photo"
}

module "members_id_photo_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id_photo.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "members_id_photo"
  description = "Get member photo"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/photo/GET"

  lambda_policy = {
    s3 = {
      actions   = ["s3:GetObject"]
      resources = ["${aws_s3_bucket.member_photos_bucket.arn}/*.jpg"]
    }

    s3_bucket = {
      actions   = ["s3:ListBucket"]
      resources = [aws_s3_bucket.member_photos_bucket.arn]
    }
  }

  lambda_env = {
    EXPIRATION        = 3600
    PHOTO_BUCKET_NAME = aws_s3_bucket.member_photos_bucket.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

module "members_id_photo_PUT" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id_photo.resource_path

  http_method = "PUT"

  prefix      = var.prefix
  name        = "members_id_photo"
  description = "Update Photo"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/{id}/photo/PUT"

  lambda_policy = {
    s3 = {
      actions   = ["s3:PutObject", "s3:DeleteObject"]
      resources = ["${aws_s3_bucket.member_photos_bucket.arn}/*.jpg"]
    }
  }

  lambda_env = {
    PHOTO_BUCKET_NAME = aws_s3_bucket.member_photos_bucket.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /members/{id}/role

module "members_id_role" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members_id.resource_id
  path_part   = "role"
}

module "members_id_role_PATCH" {
  source     = "./api_method_dynamodb"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_id_role.resource_path

  http_method = "PATCH"

  prefix = var.prefix
  name   = "members_id_role"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action    = "UpdateItem"
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

# /members/report

module "members_report" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "report"
}

module "members_report_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_report.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "members_report"
  description = "Generate membership report"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/report/GET"

  lambda_policy = {
    members = {
      actions = [
        "dynamodb:GetItem",
        "dynamodb:Scan"
      ]
      resources = [aws_dynamodb_table.members_table.arn]
    }
  }

  lambda_env = {
    MEMBERS_TABLE = aws_dynamodb_table.members_table.name
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}


# /members/awards

module "members_awards" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.members.resource_id
  path_part   = "awards"
}

module "members_awards_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.members_awards.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "members_awards"
  description = "Generate a list of members to consider for good service awards"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/members/awards/GET"

  lambda_policy = {
    events = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn,
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    allocations = {
      actions = [
        "dynamodb:Query"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn,
        "${aws_dynamodb_table.event_allocation_table.arn}/index/${var.prefix}-member_event_allocations"
      ]
    }

    members = {
      actions = [
        "dynamodb:Scan"
      ]
      resources = [
        aws_dynamodb_table.members_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_INDEX = "${var.prefix}-member_event_allocations"
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE      = aws_dynamodb_table.event_series_table.id
    MEMBERS_TABLE           = aws_dynamodb_table.members_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}