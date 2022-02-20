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

  stream_enabled = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
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

# Lambda - Delete Inactive Members

module "delete_accounts" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = "${path.module}/lambda/cron/delete_accounts"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-delete_accounts-lambda"
  description = "Delete inactive accounts"
  handler = "index.handler"
  runtime = "python3.9"

  attach_cloudwatch_logs_policy = true

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      actions = [
        "dynamodb:Query",
        "dynamodb:DeleteItem"
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
        aws_ses_template.account_deleted.arn,
        aws_ses_template.account_deleted_soon.arn,
        data.aws_ses_domain_identity.qswp.arn
      ]
    }
  }

  role_name = "${var.prefix}-delete_accounts-role"

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
    DELETED_SOON_TEMPLATE = aws_ses_template.account_deleted_soon.name,
    ACCOUNT_DELETED_TEMPLATE = aws_ses_template.account_deleted.name
  }
}

resource "aws_cloudwatch_event_target" "delete_accounts" {
    rule = aws_cloudwatch_event_rule.daily_0700.name
    arn = module.delete_accounts.lambda_function_arn
}

# SES Templates

resource "aws_ses_template" "membership_expires_soon" {
  name    = "${var.prefix}-membership_expires_soon"
  subject = "Your QSWP membership will expire soon"
  html    = file("${path.module}/emails/membership_expires_soon.html")
}

resource "aws_ses_template" "membership_expired" {
  name    = "${var.prefix}-membership_expired"
  subject = "Your QSWP membership has expired"
  html    = file("${path.module}/emails/membership_expired.html")
}

resource "aws_ses_template" "account_deleted_soon" {
  name    = "${var.prefix}-account_deleted_soon"
  subject = "Your QSWP account will be deleted soon"
  html    = file("${path.module}/emails/account_deleted_soon.html")
}

resource "aws_ses_template" "account_deleted" {
  name    = "${var.prefix}-account_deleted"
  subject = "Your QSWP account has been deleted"
  html    = file("${path.module}/emails/account_deleted.html")
}

# Lambda - Sync changes to Cognito

module "sync_members" {
  source = "terraform-aws-modules/lambda/aws"

  source_path = [
    {
      path = "${path.module}/lambda/sync/members"
      pip_requirements = false
    }
  ]

  function_name = "${var.prefix}-sync_members-lambda"
  description = "Sync members DynamoDB table to Cognito"
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
        "${aws_dynamodb_table.members_table.arn}/stream/*"
      ]
    }

    cognito = {
      actions = [
        "cognito-idp:AdminCreateUser",
        "cognito-idp:AdminDeleteUser",
        "cognito-idp:AdminUpdateUserAttributes"
      ]
      resources = [
        aws_cognito_user_pool.portal.arn
      ]
    }
  }

  role_name = "${var.prefix}-sync_members-role"

  publish = true

  timeout = 300
  memory_size = 512

  environment_variables = {
    USER_POOL = aws_cognito_user_pool.portal.id
    GROUP = aws_cognito_user_group.standard.name
  }
}

resource "aws_lambda_event_source_mapping" "sync_members" {
  event_source_arn  = aws_dynamodb_table.members_table.stream_arn
  function_name     = module.sync_members.lambda_function_arn
  starting_position = "LATEST"
}