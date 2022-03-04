# DynamoDB
resource "aws_dynamodb_table" "applications_table" {
  name = "${var.prefix}-applications"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "membershipNumber"

  attribute {
    name = "membershipNumber"
    type = "S"
  }
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
