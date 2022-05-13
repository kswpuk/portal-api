# DynamoDB
resource "aws_dynamodb_table" "applications_table" {
  name = "${var.prefix}-applications"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "membershipNumber"

  attribute {
    name = "membershipNumber"
    type = "S"
  }

  stream_enabled = true
  stream_view_type = "NEW_IMAGE"
}

resource "aws_dynamodb_table" "references_table" {
  name = "${var.prefix}-references"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "membershipNumber"
  range_key = "referenceEmail"

  attribute {
    name = "membershipNumber"
    type = "S"
  }

  attribute {
    name = "referenceEmail"
    type = "S"
  }

  stream_enabled = true
  stream_view_type = "NEW_IMAGE"
}

# S3 Bucket
resource "aws_s3_bucket" "applications_evidence_bucket" {
  bucket_prefix = "${var.prefix}-applications-evidence"
}

resource "aws_s3_bucket_acl" "applications_evidence_bucket" {
  bucket = aws_s3_bucket.applications_evidence_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "applications_evidence_bucket" {
  bucket = aws_s3_bucket.applications_evidence_bucket.id

  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

# SES Templates

resource "aws_ses_template" "application_received" {
  name    = "${var.prefix}-application_received"
  subject = "QSWP - Application Received"
  html    = file("${path.module}/emails/application_received.html")
}

resource "aws_ses_template" "reference_request" {
  name    = "${var.prefix}-reference_request"
  subject = "QSWP - Request for Reference"
  html    = file("${path.module}/emails/reference_request.html")
}

resource "aws_ses_template" "reference_received" {
  name    = "${var.prefix}-reference_received"
  subject = "QSWP - Reference Received"
  html    = file("${path.module}/emails/reference_received.html")
}

# Sync applications and trigger actions
module "sync_applications" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = "${path.module}/lambda/sync/applications"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-sync_applications-lambda"
  description = "Sync applications DynamoDB table to evidence S3 bucket and references DynamoDB table, and send e-mails"
  handler = "index.handler"
  runtime = "python3.9"

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ]
      resources = [ 
        "${aws_dynamodb_table.applications_table.arn}/stream/*"
      ]
    }

    s3 = {
      actions = [
        "s3:DeleteObject"
      ]
      resources = [
        "${aws_s3_bucket.applications_evidence_bucket.arn}/*"
      ]
    }

    dynamodb_references = {
      actions = [
        "dynamodb:Query",
        "dynamodb:DeleteItem"
      ]
      resources = [ 
        aws_dynamodb_table.references_table.arn
      ]
    }

    ses = {
      actions = [
        "ses:SendTemplatedEmail"
      ]
      resources = [
        aws_ses_template.application_received.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-sync_applications-role"

  publish = true

  timeout = 300
  memory_size = 512

  environment_variables = {
    APPLICATION_RECEIVED_TEMPLATE = aws_ses_template.application_received.name
    EVIDENCE_BUCKET_NAME = aws_s3_bucket.applications_evidence_bucket.id
    MEMBERS_EMAIL = var.members_email
    PORTAL_DOMAIN = aws_route53_record.portal.fqdn
    REFERENCES_TABLE = aws_dynamodb_table.references_table.name
  }
}

resource "aws_lambda_event_source_mapping" "sync_applications" {
  event_source_arn  = aws_dynamodb_table.applications_table.stream_arn
  function_name     = module.sync_applications.lambda_function_arn
  starting_position = "LATEST"
}

# Sync references and trigger actions
module "sync_references" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = "${path.module}/lambda/sync/references"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-sync_references-lambda"
  description = "Send e-mails as data is inserted/updated in references DynamoDB table"
  handler = "index.handler"
  runtime = "python3.9"

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ]
      resources = [ 
        "${aws_dynamodb_table.references_table.arn}/stream/*"
      ]
    }

    dynamodb_applications = {
      actions = [ "dynamodb:GetItem" ]
      resources = [ aws_dynamodb_table.applications_table.arn ]
      condition = {
        forallvalues_condition = {
          test = "ForAllValues:StringEquals"
          variable = "dynamodb:Attributes"
          values = ["membershipNumber","firstName","surname","email"]
        }
        stringequals_condition = {
          test = "StringEquals"
          variable = "dynamodb:Select"
          values = ["SPECIFIC_ATTRIBUTES"]
        }
      }
    }

    ses = {
      actions = [
        "ses:SendTemplatedEmail"
      ]
      resources = [
        aws_ses_template.reference_request.arn,
        aws_ses_template.reference_received.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-sync_references-role"

  publish = true

  timeout = 300
  memory_size = 512

  environment_variables = {
    APPLICATION_TABLE = aws_dynamodb_table.applications_table.name
    MEMBERS_EMAIL = var.members_email
    PORTAL_DOMAIN = aws_route53_record.portal.fqdn
    REFERENCE_REQUEST_TEMPLATE = aws_ses_template.reference_request.name
    REFERENCE_RECEIVED_TEMPLATE = aws_ses_template.reference_received.name
  }
}

resource "aws_lambda_event_source_mapping" "sync_references" {
  event_source_arn  = aws_dynamodb_table.references_table.stream_arn
  function_name     = module.sync_references.lambda_function_arn
  starting_position = "LATEST"
}