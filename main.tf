locals {
  lambda_assume_role_policy = {
    lambda = {
      actions = ["sts:AssumeRole"]
      principals = {
        lambda_principal = {
          type = "Service"
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
    #set($value = $util.escapeJavaScript($item.get($key).get($type)))
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
      #set($value = $util.escapeJavaScript($item.get($key).get($type)))
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
    name = "${var.prefix}-daily_0700"
    description = "Fires daily at 0700"
    schedule_expression = "cron(0 7 * * ? *)"
}

# Data

data "aws_ses_domain_identity" "qswp" {
  domain = "qswp.org.uk"
}

data "aws_region" "current" {}


# Secrets

resource "aws_secretsmanager_secret" "stripe" {
  name = "${var.prefix}-stripe"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "stripe" {
  secret_id     = aws_secretsmanager_secret.stripe.id
  secret_string = var.stripe_api_key
}