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

variable "events_email" {
  type = string
  default = "\"QSWP Events Coordinator\" <events@qswp.org.uk>"
}

variable "members_email" {
  type = string
  default = "\"QSWP Membership Coordinator\" <members@qswp.org.uk>"
}

variable "money_email" {
  type = string
  default = "\"QSWP Treasurer\" <money@qswp.org.uk>"
}