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

module "applications_id_POST" {
  source = "./api_method_lambda"
  
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

# /applications/{id}/head
module "applications_id_head" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id.resource_id
  path_part   = "head"
}

module "applications_id_head_GET" {
  source = "./api_method_dynamodb"
  
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

module "applications_id_references_POST" {
  source = "./api_method_lambda"
  
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

# /applications/{id}/evidence

module "applications_id_evidence" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.applications_id.resource_id
  path_part   = "evidence"
}

module "applications_id_evidence_GET" {
  source = "./api_method_s3"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.applications_id_evidence.resource_path

  http_method = "GET"

  prefix = var.prefix
  name = "applications_id_evidence"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  s3_bucket = aws_s3_bucket.applications_evidence_bucket.id
  s3_suffix = ".jpg"
}