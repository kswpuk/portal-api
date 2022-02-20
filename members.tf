# DynamoDB
resource "aws_dynamodb_table" "members_table" {
  name = "${var.prefix}-members"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "membershipNumber"

  attribute {
    name = "membershipNumber"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "membershipExpires"
    type = "S"
  }

  global_secondary_index {
    name               = "${var.prefix}-membership_status"
    hash_key           = "status"
    range_key          = "membershipExpires"
    projection_type    = "ALL"
  }
}

# S3 Bucket
resource "aws_s3_bucket" "member_photos_bucket" {
  bucket_prefix = "${var.prefix}-member-photos"
}

resource "aws_s3_bucket_acl" "member_photos_bucket" {
  bucket = aws_s3_bucket.member_photos_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "member_photos_bucket" {
  bucket = aws_s3_bucket.member_photos_bucket.id

  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

# Lambda - Expire Members

module "expire_membership" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = "${path.module}/lambda/cron/expire_membership"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-expire_membership-lambda"
  description = "Expire membership"
  handler = "index.handler"
  runtime = "python3.9"

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [
        "dynamodb:Query",
        "dynamodb:UpdateItem"
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
        aws_ses_template.membership_expired.arn,
        aws_ses_template.membership_expires_soon.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-expire_membership-role"

  publish = true
  allowed_triggers = {
    eventbridge = {
      principal  = "events.amazonaws.com"
      source_arn = aws_cloudwatch_event_rule.daily_0700.arn
    }
  }

  timeout = 300
  memory_size = 512

  environment_variables = {
    TABLE_NAME = aws_dynamodb_table.members_table.name,
    STATUS_INDEX_NAME = "${var.prefix}-membership_status",
    EXPIRES_SOON_TEMPLATE = aws_ses_template.membership_expires_soon.name,
    MEMBERSHIP_EXPIRED_TEMPLATE = aws_ses_template.membership_expired.name
  }
}

resource "aws_cloudwatch_event_target" "expire_membership" {
    rule = aws_cloudwatch_event_rule.daily_0700.name
    arn = module.expire_membership.lambda_function_arn
}

# TODO: Lambda - Delete Inactive Members

# SES Templates

data "aws_ses_domain_identity" "qswp" {
  domain = "qswp.org.uk"
}

resource "aws_ses_template" "membership_expired" {
  name    = "${var.prefix}-membership_expired"
  subject = "QSWP Membership Expired"
  html    = file("${path.module}/emails/membership_expired.html")
}

resource "aws_ses_template" "membership_expires_soon" {
  name    = "${var.prefix}-membership_expires_soon"
  subject = "QSWP Membership Expires Soon"
  html    = file("${path.module}/emails/membership_expires_soon.html")
}