module "utils_events_eligible" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = "${path.module}/lambda/utils/events/eligible"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-utils_events_eligible-lambda"
  description = "Check eligibility to attend an event"
  handler = "index.handler"
  runtime = "python3.9"

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

  timeout = 30
  memory_size = 512

  environment_variables = {
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.name
    MEMBERS_TABLE = aws_dynamodb_table.members_table.name
  }
}