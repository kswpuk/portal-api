variable "default_tags" {
  type = map
}

variable "prefix" {
  type = string
}

variable "mailchimp_api_key" {
  type = string
}

variable "mailchimp_list_id" {
  type = string
}

variable "mailchimp_server_prefix" {
  type = string
}

variable "stripe_api_key" {
  type = string
}

variable "domain" {
  type = string
  default = "qswp.org.uk"
}