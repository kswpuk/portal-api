# DynamoDB
resource "aws_dynamodb_table" "event_series_table" {
  name         = "${var.prefix}-event_series"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "eventSeriesId"

  attribute {
    name = "eventSeriesId"
    type = "S"
  }
}

resource "aws_dynamodb_table" "event_instance_table" {
  name         = "${var.prefix}-event_instances"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "eventSeriesId"
  range_key    = "eventId"

  attribute {
    name = "eventSeriesId"
    type = "S"
  }

  attribute {
    name = "eventId"
    type = "S"
  }

  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"
}

resource "aws_dynamodb_table" "event_allocation_table" {
  name         = "${var.prefix}-event_allocations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "combinedEventId"
  range_key    = "membershipNumber"

  attribute {
    name = "combinedEventId"
    type = "S"
  }

  attribute {
    name = "membershipNumber"
    type = "S"
  }

  global_secondary_index {
    name            = "${var.prefix}-member_event_allocations"
    hash_key        = "membershipNumber"
    projection_type = "ALL"
  }

  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"
}

# SES Templates

resource "aws_ses_template" "event_added" {
  name    = "${var.prefix}-event_added"
  subject = "A new KSWP event has been added"
  html    = file("${path.module}/emails/event_added.html")
}

resource "aws_ses_template" "event_allocation" {
  name    = "${var.prefix}-event_allocation"
  subject = "Your allocation has been updated for an event"
  html    = file("${path.module}/emails/event_allocation.html")
}

resource "aws_ses_template" "event_allocation_reminder" {
  name    = "${var.prefix}-event_allocation_reminder"
  subject = "Event Allocation Reminder"
  html    = file("${path.module}/emails/event_allocation_reminder.html")
}

resource "aws_ses_template" "event_reminder" {
  name    = "${var.prefix}-event_reminder"
  subject = "Event Reminder"
  html    = file("${path.module}/emails/event_reminder.html")
}

# Lambda - New Event Notification, Remove allocations on Deleted Event
module "sync_events" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/sync/events"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-sync_events-lambda"
  description   = "Send out event notifications and tidy up after event deletion"
  handler       = "index.handler"

  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb_stream = {
      actions = [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.stream_arn
      ]
    }

    dynamodb_allocations = {
      actions = [
        "dynamodb:Query",
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }

    dynamodb_events = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    dynamodb_members = {
      actions = [
        "dynamodb:Query"
      ]
      resources = [
        aws_dynamodb_table.members_table.arn,
        "${aws_dynamodb_table.members_table.arn}/index/*"
      ]
    }

    ses = {
      actions = [
        "ses:SendTemplatedEmail"
      ]
      resources = [
        aws_ses_template.event_added.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-sync_events-role"

  publish = true

  timeout     = 300
  memory_size = 512

  environment_variables = {
    ALLOCATIONS_TABLE    = aws_dynamodb_table.event_allocation_table.name
    EVENT_ADDED_TEMPLATE = aws_ses_template.event_added.name
    EVENT_SERIES_TABLE   = aws_dynamodb_table.event_series_table.name
    EVENTS_EMAIL         = var.events_email
    MEMBERS_STATUS_INDEX = "${var.prefix}-membership_status"
    MEMBERS_TABLE        = aws_dynamodb_table.members_table.name
    PORTAL_DOMAIN        = aws_route53_record.portal.fqdn
  }
}

resource "aws_lambda_event_source_mapping" "sync_events" {
  event_source_arn  = aws_dynamodb_table.event_instance_table.stream_arn
  function_name     = module.sync_events.lambda_function_arn
  starting_position = "LATEST"
}

# Lambda - New Allocation Notification
module "sync_allocations" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/sync/allocations"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-sync_allocations-lambda"
  description   = "Send out allocation notifications"
  handler       = "index.handler"

  runtime       = local.lambda_runtime
  architectures = local.lambda_architecture

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb_stream = {
      actions = [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.stream_arn
      ]
    }

    dynamodb_events = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    dynamodb_members = {
      actions = [
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.members_table.arn
      ]
    }

    ses = {
      actions = [
        "ses:SendTemplatedEmail"
      ]
      resources = [
        aws_ses_template.event_allocation.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-sync_allocations-role"

  publish = true

  timeout     = 300
  memory_size = 512

  environment_variables = {
    EVENT_ALLOCATION_TEMPLATE = aws_ses_template.event_allocation.name
    EVENT_SERIES_TABLE        = aws_dynamodb_table.event_series_table.name
    EVENTS_EMAIL              = var.events_email
    MEMBERS_TABLE             = aws_dynamodb_table.members_table.name
  }
}

resource "aws_lambda_event_source_mapping" "sync_allocations" {
  event_source_arn  = aws_dynamodb_table.event_allocation_table.stream_arn
  function_name     = module.sync_allocations.lambda_function_arn
  starting_position = "LATEST"
}

# Lambda - Allocation Reminder

module "event_allocation_reminder" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/cron/event_allocation_reminder"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-event_allocation_reminder-lambda"
  description   = "Event allocation reminder"
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
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    dynamodb_scan = {
      actions = [
        "dynamodb:Scan",
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    ses = {
      actions = [
        "ses:SendTemplatedEmail"
      ]
      resources = [
        aws_ses_template.event_allocation_reminder.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-event_allocation_reminder-role"

  publish = true
  allowed_triggers = {
    eventbridge = {
      principal  = "events.amazonaws.com"
      source_arn = aws_cloudwatch_event_rule.daily_0700.arn
    }
  }

  timeout     = 300
  memory_size = 512

  environment_variables = {
    ALLOCATION_REMINDER_TEMPLATE = aws_ses_template.event_allocation_reminder.name
    EVENT_INSTANCE_TABLE         = aws_dynamodb_table.event_instance_table.name
    EVENT_SERIES_TABLE           = aws_dynamodb_table.event_series_table.name
    EVENTS_EMAIL                 = var.events_email
    PORTAL_DOMAIN                = aws_route53_record.portal.fqdn
  }
}

resource "aws_cloudwatch_event_target" "event_allocation_reminder" {
  rule = aws_cloudwatch_event_rule.daily_0700.name
  arn  = module.event_allocation_reminder.lambda_function_arn
}


# Lambda - Event Reminder

module "event_reminder" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path             = "${path.module}/lambda/cron/event_reminder"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-event_reminder-lambda"
  description   = "Event reminder"
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
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    dynamodb_scan = {
      actions = [
        "dynamodb:Scan",
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    ses = {
      actions = [
        "ses:SendTemplatedEmail"
      ]
      resources = [
        aws_ses_template.event_reminder.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-event_reminder-role"

  publish = true
  allowed_triggers = {
    eventbridge = {
      principal  = "events.amazonaws.com"
      source_arn = aws_cloudwatch_event_rule.monthly.arn
    }
  }

  timeout     = 300
  memory_size = 512

  environment_variables = {
    EVENT_INSTANCE_TABLE    = aws_dynamodb_table.event_instance_table.name
    EVENT_REMINDER_TEMPLATE = aws_ses_template.event_reminder.name
    EVENT_SERIES_TABLE      = aws_dynamodb_table.event_series_table.name
    EVENTS_EMAIL            = var.events_email
    PORTAL_DOMAIN           = aws_route53_record.portal.fqdn
  }
}

resource "aws_cloudwatch_event_target" "event_reminder" {
  rule = aws_cloudwatch_event_rule.monthly.name
  arn  = module.event_reminder.lambda_function_arn
}