variable "rest_api_name" {
  type = string
}

variable "path" {
  type = string
}

variable "http_method" {
  type = string
}

variable "prefix" {
  type = string
}

variable "name" {
  type = string
}

variable "authorizer_id" {
  type = string
  default = ""
}

variable "dynamodb_action" {
  type = string
  default = "Query"
}

variable "dynamodb_table_arn" {
  type = string
}

variable "request_template" {
  type = string
}

variable "response_template" {
  type = string
  default = ""
}