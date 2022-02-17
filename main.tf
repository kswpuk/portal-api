locals {
  lambda_assume_role_policy = {
    lambda = {
      actions = ["sts:AssumeRole"]
      principals = {
        lambda_principal = {
          type = "Service"
          identifiers = ["lambda.amazonaws.com"]
        }
      }
    }
  }
}
