# /events

module "events" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "events"
}

module "events_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "events"
  description = "List events"

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
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE      = aws_dynamodb_table.event_series_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/_series
module "events_series" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events.resource_id
  path_part   = "_series"
}

module "events_series_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_series.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "events_series"
  description = "List event series"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/_series/GET"

  lambda_policy = {
    dynamodb = {
      actions = ["dynamodb:Scan"]
      resources = [
        aws_dynamodb_table.event_instance_table.arn,
        aws_dynamodb_table.event_series_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE   = aws_dynamodb_table.event_series_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/{seriesId}

module "events_seriesId" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events.resource_id
  path_part   = "{seriesId}"
}

module "events_seriesId_GET" {
  source     = "./api_method_dynamodb"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId.resource_path

  http_method = "GET"

  prefix = var.prefix
  name   = "events_seriesId"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  dynamodb_action    = "Query"
  dynamodb_table_arn = aws_dynamodb_table.event_series_table.arn

  request_template = <<END
{
  "TableName": "${aws_dynamodb_table.event_series_table.name}",
  "KeyConditionExpression": "eventSeriesId = :v",
  "ExpressionAttributeValues": {
    ":v": {
      "S": "$util.escapeJavaScript($input.params("seriesId"))"
    }
  }
}
END

  response_template = local.dynamodb_to_item_vtl
}

module "events_seriesId_DELETE" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId.resource_path

  http_method = "DELETE"

  prefix      = var.prefix
  name        = "events_seriesId"
  description = "Delete event series"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/DELETE"

  lambda_policy = {
    dynamodb_get = {
      actions = ["dynamodb:GetItem"]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    dynamodb_query = {
      actions = ["dynamodb:Query"]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    dynamodb_delete = {
      actions = [
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_INSTANCE_TABLE_NAME = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE_NAME   = aws_dynamodb_table.event_series_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

module "events_seriesId_POST" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId.resource_path

  http_method = "POST"

  prefix      = var.prefix
  name        = "events_seriesId"
  description = "Create event series"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/POST"

  lambda_policy = {
    dynamodb_get = {
      actions   = ["dynamodb:GetItem"]
      resources = [aws_dynamodb_table.event_series_table.arn]
      condition = {
        forallvalues_condition = {
          test     = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values   = ["eventSeriesId"]
        }
        stringequals_condition = {
          test     = "StringEquals"
          variable = "dynamodb:Select"
          values   = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }


    dynamodb_put = {
      actions = [
        "dynamodb:PutItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_SERIES_TABLE_NAME = aws_dynamodb_table.event_series_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

module "events_seriesId_PUT" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId.resource_path

  http_method = "PUT"

  prefix      = var.prefix
  name        = "events_seriesId"
  description = "Update event series"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/PUT"

  lambda_policy = {
    dynamodb_get = {
      actions   = ["dynamodb:GetItem"]
      resources = [aws_dynamodb_table.event_series_table.arn]
      condition = {
        forallvalues_condition = {
          test     = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values   = ["eventSeriesId"]
        }
        stringequals_condition = {
          test     = "StringEquals"
          variable = "dynamodb:Select"
          values   = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }


    dynamodb_update = {
      actions = [
        "dynamodb:UpdateItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_SERIES_TABLE_NAME = aws_dynamodb_table.event_series_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/{seriesId}/{eventId}

module "events_seriesId_eventId" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId.resource_id
  path_part   = "{eventId}"
}

module "events_seriesId_eventId_DELETE" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId.resource_path

  http_method = "DELETE"

  prefix      = var.prefix
  name        = "events_seriesId_eventId"
  description = "Delete event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/DELETE"

  lambda_policy = {
    dynamodb_get = {
      actions = [
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

module "events_seriesId_eventId_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "events_seriesId_eventId"
  description = "Get event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/GET"

  lambda_policy = {
    dynamodb_get = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn,
        aws_dynamodb_table.event_instance_table.arn,
        aws_dynamodb_table.members_table.arn
      ]
    }

    dynamodb_query = {
      actions = [
        "dynamodb:Query"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_events_eligible.lambda_function_arn
      ]
    }
  }

  lambda_env = {
    COMMITTEE_GROUP         = aws_cognito_user_group.committee.name
    ELIGIBILITY_ARN         = module.utils_events_eligible.lambda_function_arn
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE      = aws_dynamodb_table.event_series_table.id
    MEMBERS_TABLE           = aws_dynamodb_table.members_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

module "events_seriesId_eventId_POST" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId.resource_path

  http_method = "POST"

  prefix      = var.prefix
  name        = "events_seriesId_eventId"
  description = "Create event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/POST"

  lambda_policy = {
    dynamodb_get = {
      actions = ["dynamodb:GetItem"]
      resources = [
        aws_dynamodb_table.event_instance_table.arn,
      ]
    }

    dynamodb_put = {
      actions = [
        "dynamodb:PutItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_events_validate.lambda_function_arn
      ]
    }
  }

  lambda_env = {
    EVENT_INSTANCE_TABLE_NAME = aws_dynamodb_table.event_instance_table.id
    VALIDATION_ARN            = module.utils_events_validate.lambda_function_arn
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

module "events_seriesId_eventId_PUT" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId.resource_path

  http_method = "PUT"

  prefix      = var.prefix
  name        = "events_seriesId_eventId"
  description = "Create event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/PUT"

  lambda_policy = {
    dynamodb_get = {
      actions = ["dynamodb:GetItem"]
      resources = [
        aws_dynamodb_table.event_instance_table.arn,
      ]
    }

    dynamodb_put = {
      actions = [
        "dynamodb:UpdateItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_events_validate.lambda_function_arn
      ]
    }
  }

  lambda_env = {
    EVENT_INSTANCE_TABLE_NAME = aws_dynamodb_table.event_instance_table.id
    VALIDATION_ARN            = module.utils_events_validate.lambda_function_arn
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/{seriesId}/{eventId}/allocate

module "events_seriesId_eventId_allocate" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId.resource_id
  path_part   = "allocate"
}


module "events_seriesId_eventId_allocate_PUT" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId_allocate.resource_path

  http_method = "PUT"

  prefix      = var.prefix
  name        = "events_seriesId_eventId_allocate"
  description = "Allocate member to event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/allocate/PUT"

  lambda_policy = {
    dynamodb_allocation = {
      actions = [
        "dynamodb:UpdateItem"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_members_suspended.lambda_function_arn
      ]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    SUSPENDED_ARN           = module.utils_members_suspended.lambda_function_arn
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/{seriesId}/{eventId}/allocate/{id}

module "events_seriesId_eventId_allocate_id" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId_allocate.resource_id
  path_part   = "{id}"
}

module "events_seriesId_eventId_allocate_id_DELETE" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId_allocate_id.resource_path

  http_method = "DELETE"

  prefix      = var.prefix
  name        = "events_seriesId_eventId_allocate_id"
  description = "Delete allocation"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/allocate/{id}/DELETE"

  lambda_policy = {
    dynamodb_allocation = {
      actions = [
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/{seriesId}/{eventId}/allocate/suggest

module "events_seriesId_eventId_allocate_suggest" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId_allocate.resource_id
  path_part   = "suggest"
}


module "events_seriesId_eventId_allocate_suggest_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId_allocate_suggest.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "events_seriesId_eventId_allocate_suggest"
  description = "Suggest allocations for an event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/allocate/suggest/GET"

  lambda_layers = [
    local.pandas_layer_arn
  ]

  lambda_policy = {
    dynamodb_getitem = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    dynamodb_query = {
      actions = [
        "dynamodb:Query"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_events_weighting.lambda_function_arn,
        module.utils_members_suspended.lambda_function_arn
      ]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    SUSPENDED_ARN           = module.utils_members_suspended.lambda_function_arn
    WEIGHTING_ARN           = module.utils_events_weighting.lambda_function_arn
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/{seriesId}/{eventId}/register

module "events_seriesId_eventId_register" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId.resource_id
  path_part   = "register"
}

# /events/{seriesId}/{eventId}/register/{id}

module "events_seriesId_eventId_register_id" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId_register.resource_id
  path_part   = "{id}"
}

module "events_seriesId_eventId_register_id_POST" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_seriesId_eventId_register_id.resource_path

  http_method = "POST"

  prefix      = var.prefix
  name        = "events_seriesId_eventId_register_id"
  description = "Register for event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/register/{id}/POST"

  lambda_policy = {
    dynamodb_event = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    dynamodb_allocation = {
      actions = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_events_eligible.lambda_function_arn,
        module.utils_members_suspended.lambda_function_arn
      ]
    }
  }

  lambda_env = {
    ELIGIBILITY_ARN         = module.utils_events_eligible.lambda_function_arn
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    SUSPENDED_ARN           = module.utils_members_suspended.lambda_function_arn
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/report

module "events_report" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events.resource_id
  path_part   = "report"
}

module "events_report_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_report.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "events_report"
  description = "Generate events report"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/report/GET"

  lambda_policy = {
    events = {
      actions = [
        "dynamodb:GetItem",
        "dynamodb:Scan"
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
      ]
    }
  }

  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE      = aws_dynamodb_table.event_series_table.id
  }

  lambda_architecture = local.lambda_architecture
  lambda_runtime      = local.lambda_runtime
}

# /events/report/attendance

module "events_report_attendance" {
  source     = "./api_resource"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_report.resource_id
  path_part   = "attendance"
}

module "events_report_attendance_GET" {
  source     = "./api_method_lambda"
  depends_on = [aws_api_gateway_rest_api.portal]

  rest_api_name = aws_api_gateway_rest_api.portal.name
  path          = module.events_report_attendance.resource_path

  http_method = "GET"

  prefix      = var.prefix
  name        = "events_report_attendance"
  description = "Generate events attendance report"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/report/attendance/GET"

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