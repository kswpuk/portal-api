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

variable "description" {
  type = string
}

variable "authorizer_id" {
  type = string
  default = ""
}

variable "lambda_path" {
  type = string
}

variable "lambda_handler" {
  type = string
  default = "index.handler"
}

variable "lambda_runtime" {
  type = string
  default = "python3.9"
}

variable "lambda_timeout" {
  type = number
  default = 10
}

variable "lambda_memory" {
  type = number
  default = 512
}

variable "lambda_env" {
  type = map
  default = {}
}

variable "lambda_policy" {
  type = map
  default = {}
}