module "utils_events_eligible" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/utils/events/eligible"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-utils_events_eligible-lambda"
  description   = "Check eligibility to attend an event"
  handler       = "index.handler"

  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn,
        aws_dynamodb_table.members_table.arn
      ]
    }
  }

  role_name = "${var.prefix}-utils_events_eligible-role"

  publish = true

  timeout     = 30
  memory_size = 512

  environment_variables = {
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.name
    MEMBERS_TABLE        = aws_dynamodb_table.members_table.name
  }
}

module "utils_events_validate" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/utils/events/validate"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-utils_events_validate-lambda"
  description   = "Validate event information"
  handler       = "index.handler"

  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }
  }

  role_name = "${var.prefix}-utils_events_validate-role"

  publish = true

  timeout     = 30
  memory_size = 512

  environment_variables = {
    EVENT_SERIES_TABLE_NAME = aws_dynamodb_table.event_series_table.name
  }
}

module "utils_events_weighting" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/utils/events/weighting"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-utils_events_weighting-lambda"
  description   = "Determine which weighting criteria a member meets"
  handler       = "index.handler"

  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb_get = {
      actions = [
        "dynamodb:GetItem",
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn,
        aws_dynamodb_table.event_series_table.arn,
        aws_dynamodb_table.members_table.arn
      ]
    }

    dynamodb_query = {
      actions = [
        "dynamodb:Query",
      ]
      resources = [
        "${aws_dynamodb_table.event_allocation_table.arn}/index/*"
      ]
    }
  }

  role_name = "${var.prefix}-utils_events_weighting-role"

  publish = true

  timeout     = 30
  memory_size = 512

  environment_variables = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_ALLOCATIONS_INDEX = "${var.prefix}-member_event_allocations"
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE      = aws_dynamodb_table.event_series_table.id
    MEMBERS_TABLE           = aws_dynamodb_table.members_table.id
  }
}

module "utils_members_future_events" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/utils/members/future_events"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-utils_members_future_events-lambda"
  description   = "List future event allocations for a member"
  handler       = "index.handler"

  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb_eventinstance = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
      condition = {
        forallvalues_condition = {
          test     = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values   = ["eventSeriesId", "eventId", "startDate"]
        }
        stringequals_condition = {
          test     = "StringEquals"
          variable = "dynamodb:Select"
          values   = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }

    dynamodb_allocations = {
      actions = [
        "dynamodb:Query"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn,
        "${aws_dynamodb_table.event_allocation_table.arn}/index/${var.prefix}-member_event_allocations"
      ]
    }
  }

  role_name = "${var.prefix}-utils_members_future_events-role"

  publish = true

  timeout     = 10
  memory_size = 512

  environment_variables = {
    ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.name
    EVENT_ALLOCATIONS_INDEX = "${var.prefix}-member_event_allocations"
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.name

    POWERTOOLS_METRICS_NAMESPACE = var.prefix
    POWERTOOLS_SERVICE_NAME      = "${var.prefix}-utils"
  }

  layers = [
    local.powertools_layer_arn
  ]
}


module "utils_members_suspended" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/utils/members/suspended"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-utils_members_suspended-lambda"
  description   = "Check whether a member is suspended"
  handler       = "index.handler"

  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.members_table.arn
      ]
      condition = {
        forallvalues_condition = {
          test     = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values   = ["membershipNumber", "suspended"]
        }
        stringequals_condition = {
          test     = "StringEquals"
          variable = "dynamodb:Select"
          values   = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }
  }

  role_name = "${var.prefix}-utils_members_suspended-role"

  publish = true

  timeout     = 10
  memory_size = 512

  environment_variables = {
    MEMBERS_TABLE        = aws_dynamodb_table.members_table.name
    POWERTOOLS_METRICS_NAMESPACE = var.prefix
    POWERTOOLS_SERVICE_NAME      = "${var.prefix}-utils"
  }

  layers = [
    local.powertools_layer_arn
  ]
}
