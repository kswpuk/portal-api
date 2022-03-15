# DynamoDB
resource "aws_dynamodb_table" "event_series_table" {
  name = "${var.prefix}-event_series"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "eventSeriesId"

  attribute {
    name = "eventSeriesId"
    type = "S"
  }
}

resource "aws_dynamodb_table" "event_instance_table" {
  name = "${var.prefix}-event_instances"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "eventSeriesId"
  range_key = "eventId"

  attribute {
    name = "eventSeriesId"
    type = "S"
  }

  attribute {
    name = "eventId"
    type = "S"
  }

  stream_enabled = true
  stream_view_type = "NEW_IMAGE"
}

resource "aws_dynamodb_table" "event_allocation_table" {
  name = "${var.prefix}-event_allocations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "combinedEventId"
  range_key = "membershipNumber"

  attribute {
    name = "combinedEventId"
    type = "S"
  }

  attribute {
    name = "membershipNumber"
    type = "S"
  }

  global_secondary_index {
    name               = "${var.prefix}-member_event_allocations"
    hash_key           = "membershipNumber"
    projection_type    = "ALL"
  }
  
  stream_enabled = true
  stream_view_type = "NEW_IMAGE"
}