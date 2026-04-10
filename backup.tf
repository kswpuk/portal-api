# TODO: Only back up if we're in prod, not in test
resource "aws_backup_vault" "backup" {
  name        = "${var.prefix}-backup"
}

resource "aws_backup_plan" "daily" {
  name = "${var.prefix}-daily-plan"

  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.backup.name
    schedule          = "cron(0 0 * * ? *)"

    lifecycle {
      delete_after = 30
    }
  }
}

resource "aws_backup_selection" "daily_selection" {
  plan_id      = aws_backup_plan.daily.id
  name         = "${var.prefix}-daily-selection"
  iam_role_arn = aws_iam_role.backup_role.arn

  resources = [
    # DynamoDB Tables
    aws_dynamodb_table.applications_table.arn,
    aws_dynamodb_table.event_allocation_table.arn,
    aws_dynamodb_table.event_instance_table.arn,
    aws_dynamodb_table.event_series_table.arn,
    aws_dynamodb_table.members_table.arn,
    aws_dynamodb_table.references_table.arn,

    # TODO: Application Evidence

    # TODO: Member Images
  ]
}

resource "aws_iam_role" "backup_role" {
  name = "${var.prefix}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "backup.amazonaws.com"
        },
        Action : "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}