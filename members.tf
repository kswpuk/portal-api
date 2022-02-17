# DynamoDB
resource "aws_dynamodb_table" "members_table" {
  name = "${var.prefix}-members"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "membershipNumber"

  attribute {
    name = "membershipNumber"
    type = "S"
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