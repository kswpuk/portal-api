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
  range_key = "referenceId"

  attribute {
    name = "membershipNumber"
    type = "S"
  }

  attribute {
    name = "referenceId"
    type = "S"
  }
}
