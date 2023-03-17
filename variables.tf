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
  default = "kswp.org.uk"
}

variable "events_email" {
  type = string
  default = "\"KSWP Events Coordinator\" <events@kswp.org.uk>"
}

variable "members_email" {
  type = string
  default = "\"KSWP Membership Coordinator\" <members@kswp.org.uk>"
}

variable "money_email" {
  type = string
  default = "\"KSWP Treasurer\" <money@kswp.org.uk>"
}