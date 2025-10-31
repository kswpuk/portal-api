resource "aws_sns_topic" "alarms" {
  name = "${var.prefix}-alarms"
}

resource "aws_sns_topic_subscription" "alarms" {
  for_each = var.alarm_emails

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = each.key
}

resource "aws_cloudwatch_metric_alarm" "applications_id_POST" {
  alarm_name                = "${var.prefix}-applications_id_POST"
  alarm_description         = "Monitor errors in submitting applications"
  
  namespace                 = "AWS/Lambda"
  metric_name               = "Errors"
  dimensions = {
    FunctionName = module.applications_id_POST.lambda_name
  }
  
  statistic                 = "Sum"
  comparison_operator       = "GreaterThanThreshold"
  threshold                 = 0
  evaluation_periods        = 1
  period                    = 300
  
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "applications_id_references_POST" {
  alarm_name                = "${var.prefix}-applications_id_references_POST"
  alarm_description         = "Monitor errors in submitting references"
  
  namespace                 = "AWS/Lambda"
  metric_name               = "Errors"
  dimensions = {
    FunctionName = module.applications_id_references_POST.lambda_name
  }
  
  statistic                 = "Sum"
  comparison_operator       = "GreaterThanThreshold"
  threshold                 = 0
  evaluation_periods        = 1
  period                    = 300
  
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "payments_membership_session_GET" {
  alarm_name                = "${var.prefix}-payments_membership_session_GET"
  alarm_description         = "Monitor errors in membership payments"
  
  namespace                 = "AWS/Lambda"
  metric_name               = "Errors"
  dimensions = {
    FunctionName = module.payments_membership_session_GET.lambda_name
  }
  
  statistic                 = "Sum"
  comparison_operator       = "GreaterThanThreshold"
  threshold                 = 0
  evaluation_periods        = 1
  period                    = 300
  
  alarm_actions       = [aws_sns_topic.alarms.arn]
}