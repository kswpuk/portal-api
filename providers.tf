terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-west-2"

  default_tags {
    tags = var.default_tags
  }
}

provider "aws" {
  alias  = "acm_provider"
  region = "us-east-1"

  default_tags {
    tags = var.default_tags
  }
}