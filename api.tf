# Logging
resource "aws_api_gateway_account" "portal" {
  cloudwatch_role_arn = aws_iam_role.agw_cloudwatch.arn
}

resource "aws_iam_role" "agw_cloudwatch" {
  name = "${var.prefix}-api_gateway_cloudwatch-role"
  assume_role_policy = data.aws_iam_policy_document.agw_assume_role_policy.json
}

resource "aws_iam_role_policy" "cloudwatch" {
  name = "${var.prefix}-api_gateway_cloudwatch-policy"
  role = aws_iam_role.agw_cloudwatch.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:*"
            ],
            "Resource": "*"
        }
    ]
}
EOF
}

# API Gateway
resource "aws_api_gateway_rest_api" "portal" {
  name = "${var.prefix}-api"
  description = "REST API for QSWP Portal"
  binary_media_types = ["image/*", "multipart/form-data"]
}

resource "aws_api_gateway_deployment" "portal" {
  rest_api_id = aws_api_gateway_rest_api.portal.id

  # FIXME: Doesn't trigger new deployments on change
  triggers = {
    modules = sha1(join("", [
      jsonencode(module.members_GET),
      jsonencode(module.members_id_GET),
      jsonencode(module.members_id_DELETE),
      jsonencode(module.members_id_PUT),
      jsonencode(module.members_id_payment_POST),
      jsonencode(module.members_id_photo_GET),
      jsonencode(module.members_id_photo_PUT),

      jsonencode(module.applications_GET),
      jsonencode(module.applications_id_GET),
      jsonencode(module.applications_id_POST),
      jsonencode(module.applications_id_approve_POST),
      jsonencode(module.applications_id_evidence_GET),
      jsonencode(module.applications_id_head_GET),
      jsonencode(module.applications_id_references_GET),
      jsonencode(module.applications_id_references_POST),
      jsonencode(module.applications_id_references_email_GET),
      jsonencode(module.applications_id_references_email_accept_PATCH),

      jsonencode(module.events_GET),
      jsonencode(module.events_series_GET),
      jsonencode(module.events_seriesId_GET),
      jsonencode(module.events_seriesId_POST),
      jsonencode(module.events_seriesId_PUT),
      jsonencode(module.events_seriesId_DELETE),
      jsonencode(module.events_seriesId_eventId_GET),
      jsonencode(module.events_seriesId_eventId_POST),
      jsonencode(module.events_seriesId_eventId_PUT),
      jsonencode(module.events_seriesId_eventId_DELETE),
      jsonencode(module.events_seriesId_eventId_allocate_PUT),
      jsonencode(module.events_seriesId_eventId_allocate_id_DELETE),
      jsonencode(module.events_seriesId_eventId_register_id_POST),

      jsonencode(module.payments_membership_session_GET)
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    module.members_GET,
    module.members_id_GET,
    module.members_id_DELETE,
    module.members_id_PUT,
    module.members_id_payment_POST,
    module.members_id_photo_GET,
    module.members_id_photo_PUT,

    module.applications_GET,
    module.applications_id_GET,
    module.applications_id_POST,
    module.applications_id_approve_POST,
    module.applications_id_evidence_GET,
    module.applications_id_head_GET,
    module.applications_id_references_GET,
    module.applications_id_references_POST,
    module.applications_id_references_email_GET,
    module.applications_id_references_email_accept_PATCH,

    module.events_GET,
    module.events_series_GET,
    module.events_seriesId_GET,
    module.events_seriesId_POST,
    module.events_seriesId_PUT,
    module.events_seriesId_DELETE,
    module.events_seriesId_eventId_GET,
    module.events_seriesId_eventId_POST,
    module.events_seriesId_eventId_PUT,
    module.events_seriesId_eventId_DELETE,
    module.events_seriesId_eventId_allocate_PUT,
    module.events_seriesId_eventId_allocate_id_DELETE,
    module.events_seriesId_eventId_register_id_POST,

    module.payments_membership_session_GET
  ]
}

resource "aws_api_gateway_stage" "portal" {
  deployment_id = aws_api_gateway_deployment.portal.id
  rest_api_id   = aws_api_gateway_rest_api.portal.id
  stage_name    = var.prefix
}

resource "aws_api_gateway_authorizer" "portal" {
  name                   = "${var.prefix}-api-auth"
  rest_api_id            = aws_api_gateway_rest_api.portal.id
  authorizer_uri         = module.auth_lambda.lambda_function_invoke_arn
  authorizer_credentials = aws_iam_role.auth_invocation_role.arn
}

# IAM

resource "aws_iam_role" "auth_invocation_role" {
  name = "${var.prefix}-agw_invoke_auth-role"
  assume_role_policy = data.aws_iam_policy_document.agw_assume_role_policy.json
}

resource "aws_iam_role_policy" "auth_invocation_policy" {
  name = "${var.prefix}-agw_invoke_auth-policy"
  role = aws_iam_role.auth_invocation_role.id

  policy = data.aws_iam_policy_document.agw_invoke_lambda_policy.json
}

data "aws_iam_policy_document" "agw_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "agw_invoke_lambda_policy" {
  statement {
    actions = ["lambda:InvokeFunction"]
    resources = [ module.auth_lambda.lambda_function_arn ]
  }
}