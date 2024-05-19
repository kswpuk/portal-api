locals {
  powertools_layer_arn = "arn:aws:lambda:${data.aws_region.current.name}:017000801446:layer:AWSLambdaPowertoolsPythonV2-Arm64:71"
  lambda_architecture  = ["arm64"]
  lambda_runtime       = "python3.12"

  lambda_assume_role_policy = {
    lambda = {
      actions = ["sts:AssumeRole"]
      principals = {
        lambda_principal = {
          type        = "Service"
          identifiers = ["lambda.amazonaws.com"]
        }
      }
    }
  }

  dynamodb_to_item_vtl = <<END
#set($item = $input.path('$.Items[0]'))
{
#foreach($key in $item.keySet())
  #foreach($type in $item.get($key).keySet())
    #set($value = $util.escapeJavaScript($item.get($key).get($type)).replaceAll("\\'","'"))
    "$key": #if($type == "S")"#end$value#if($type == "S")"#end
  #end
  #if($foreach.hasNext),#end
#end
}
END

  dynamodb_to_array_vtl = <<END
#set($inputRoot = $input.path('$'))
[
#foreach($item in $inputRoot.Items) {
  #foreach($key in $item.keySet())
    #foreach($type in $item.get($key).keySet())
      #set($value = $util.escapeJavaScript($item.get($key).get($type)).replaceAll("\\'","'"))
      "$key": #if($type == "S")"#end$value#if($type == "S")"#end
    #end
    #if($foreach.hasNext),#end
  #end 
}
#if($foreach.hasNext),#end
#end
]
END
}

# Cron Timings

resource "aws_cloudwatch_event_rule" "daily_0700" {
  name                = "${var.prefix}-daily_0700"
  description         = "Fires daily at 0700"
  schedule_expression = "cron(0 7 * * ? *)"
}

resource "aws_cloudwatch_event_rule" "weekly" {
  name                = "${var.prefix}-weekly"
  description         = "Fires on Fridays at 0700"
  schedule_expression = "cron(0 7 ? * FRI *)"
}

resource "aws_cloudwatch_event_rule" "monthly" {
  name                = "${var.prefix}-monthly"
  description         = "Fires on first of month at 0900"
  schedule_expression = "cron(0 9 1 * ? *)"
}

# Data

data "aws_ses_domain_identity" "qswp" {
  domain = var.domain
}

data "aws_region" "current" {}


# Secrets

resource "aws_secretsmanager_secret" "api_keys" {
  name                    = "${var.prefix}-api_keys"
  description             = "API keys for external services used by the Portal"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    mailchimp = var.mailchimp_api_key
    stripe    = var.stripe_api_key
  })
}