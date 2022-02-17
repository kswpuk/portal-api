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

variable "s3_bucket" {
  type = string
}

variable "s3_prefix" {
  type = string
  default = ""
}

variable "s3_suffix" {
  type = string
  default = ""
}

variable "path_key" {
  type = string
  default = "id"
}