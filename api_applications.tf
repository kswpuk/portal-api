# /applications

module "applications" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "applications"
}

module "applications_GET" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "applications"
  description = "List applications"

  lambda_path = "${path.module}/lambda/api/applications/GET"

  lambda_policy = {
    dynamodb = {
      actions = [ "dynamodb:Scan" ]
      resources = [ aws_dynamodb_table.applications_table.arn, aws_dynamodb_table.references_table.arn ]
    }
  }
  
  lambda_env = {
    APPLICATIONS_TABLE = aws_dynamodb_table.applications_table.id
    REFERENCES_TABLE = aws_dynamodb_table.references_table.id
  }
}

# /applications/{id}

module "applications_id" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications.resource_id
  path_part   = "{id}"
}

module "applications_id_GET" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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

module "applications_id_POST" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id.resource_path

  http_method   = "POST"

  prefix = var.prefix
  name = "applications_id"
  description = "Submit Application"

  lambda_path = "${path.module}/lambda/api/applications/{id}/POST"

  lambda_policy = {
    dynamodb_put = {
      actions = [ "dynamodb:PutItem" ]
      resources = [ 
        aws_dynamodb_table.applications_table.arn,
        aws_dynamodb_table.references_table.arn
      ]
    }

    dynamodb_applications_get = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.applications_table.arn ]
      condition = {
        forallvalues_condition = {
          test = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values = ["membershipNumber"]
        }
        stringequals_condition = {
          test = "StringEquals"
          variable = "dynamodb:Select"
          values = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }

    dynamodb_members = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.members_table.arn ]
      condition = {
        forallvalues_condition = {
          test = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values = ["membershipNumber"]
        }
        stringequals_condition = {
          test = "StringEquals"
          variable = "dynamodb:Select"
          values = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }

    s3 = {
      actions = [ "s3:PutObject" ]
      resources = [ "${aws_s3_bucket.applications_evidence_bucket.arn}/*.jpg" ]
    }
  }
  
  lambda_env = {
    APPLICATIONS_TABLE_NAME = aws_dynamodb_table.applications_table.id
    MEMBERS_TABLE_NAME = aws_dynamodb_table.members_table.id
    REFERENCES_TABLE_NAME = aws_dynamodb_table.references_table.id
    EVIDENCE_BUCKET_NAME = aws_s3_bucket.applications_evidence_bucket.id
  }
}

# /applications/{id}/approve

module "applications_id_approve" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id.resource_id
  path_part   = "approve"
}

module "applications_id_approve_POST" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_approve.resource_path

  http_method   = "POST"

  prefix = var.prefix
  name = "applications_id_approve"
  description = "Approve Application"

  lambda_path = "${path.module}/lambda/api/applications/{id}/approve/POST"

  lambda_policy = {
    dynamodb_members = {
      actions = [
        "dynamodb:PutItem"
      ]
      resources = [ 
        aws_dynamodb_table.members_table.arn
      ]
    }

    dynamodb_applications = {
      actions = [
        "dynamodb:GetItem",
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.applications_table.arn
      ]
    }
  }
  
  lambda_env = {
    APPLICATIONS_TABLE_NAME = aws_dynamodb_table.applications_table.id
    MEMBERS_TABLE_NAME = aws_dynamodb_table.members_table.id
  }
}

# /applications/{id}/evidence

module "applications_id_evidence" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id.resource_id
  path_part   = "evidence"
}

module "applications_id_evidence_GET" {
  source = "./api_method_s3"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_evidence.resource_path

  http_method = "GET"

  prefix = var.prefix
  name = "applications_id_evidence"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  s3_bucket = aws_s3_bucket.applications_evidence_bucket.id
  s3_suffix = ".jpg"
}

# /applications/{id}/head
module "applications_id_head" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id.resource_id
  path_part   = "head"
}

module "applications_id_head_GET" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_head.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "applications_id_head"

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
  },
  "ProjectionExpression": "firstName,surname"
}
END

  response_template = local.dynamodb_to_item_vtl
}

# /applications/{id}/references

module "applications_id_references" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id.resource_id
  path_part   = "references"
}

module "applications_id_references_GET" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
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
  },
  "ProjectionExpression": "referenceName,referenceEmail,relationship,howLong,submittedAt,accepted"
}
END

  response_template = local.dynamodb_to_array_vtl
}

module "applications_id_references_POST" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_references.resource_path

  http_method   = "POST"

  prefix = var.prefix
  name = "applications_id_references"
  description = "Submit Reference"

  lambda_path = "${path.module}/lambda/api/applications/{id}/references/POST"

  lambda_policy = {
    dynamodb_put = {
      actions = [ "dynamodb:PutItem" ]
      resources = [ 
        aws_dynamodb_table.references_table.arn
      ]
    }

    dynamodb_applications_get = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.applications_table.arn ]
      condition = {
        forallvalues_condition = {
          test = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values = ["membershipNumber"]
        }
        stringequals_condition = {
          test = "StringEquals"
          variable = "dynamodb:Select"
          values = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }

    dynamodb_references_get = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.references_table.arn ]
      condition = {
        forallvalues_condition = {
          test = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values = ["membershipNumber", "referenceEmail", "relationship"]
        }
        stringequals_condition = {
          test = "StringEquals"
          variable = "dynamodb:Select"
          values = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }
  }
  
  lambda_env = {
    APPLICATIONS_TABLE_NAME = aws_dynamodb_table.applications_table.id
    REFERENCES_TABLE_NAME = aws_dynamodb_table.references_table.id
  }
}

# /applications/{id}/references/{email}

module "applications_id_references_email" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id_references.resource_id
  path_part   = "{email}"
}

module "applications_id_references_email_GET" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_references_email.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "applications_id_references_email"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "Query"
  dynamodb_table_arn = aws_dynamodb_table.references_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.references_table.name}",
  "KeyConditionExpression": "membershipNumber = :v and referenceEmail =:e",
  "ExpressionAttributeValues": {
    ":v": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    },
    ":e": {
      "S": "$util.escapeJavaScript($input.params("email"))"
    }
  }
}
END

  response_template = local.dynamodb_to_item_vtl
}

# /applications/{id}/references/{email}/accept

module "applications_id_references_email_accept" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id_references_email.resource_id
  path_part   = "accept"
}

module "applications_id_references_email_accept_PATCH" {
  source = "./api_method_dynamodb"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_references_email_accept.resource_path

  http_method   = "PATCH"

  prefix = var.prefix
  name = "applications_id_references_email_accept"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action = "UpdateItem"
  dynamodb_table_arn = aws_dynamodb_table.references_table.arn

  
  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.references_table.name}",
  "Key": {
    "membershipNumber": {
      "S": "$util.escapeJavaScript($input.params("id"))"
    },
    "referenceEmail": {
      "S": "$util.escapeJavaScript($input.params("email"))"
    }
  },
  "UpdateExpression": "SET accepted = :v",
  "ExpressionAttributeValues": {
    ":v": {
      "BOOL": #if( $input.json('$.accepted') == false ) false #else true #end
    }
  }
}
END
}