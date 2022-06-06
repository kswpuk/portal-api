# /socials

module "socials" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "socials"
}

# /socials/{seriesId}

module "socials_seriesId" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.socials.resource_id
  path_part   = "{seriesId}"
}

# /socials/{seriesId}/{eventId}

module "socials_seriesId_eventId" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.socials_seriesId.resource_id
  path_part   = "{eventId}"
}

module "socials_seriesId_eventId_ANY" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.socials_seriesId_eventId.resource_path

  http_method = "ANY"

  prefix = var.prefix
  name = "socials_seriesId_eventId"
  description = "Socials proxy"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/socials/{seriesId}/{eventId}/ANY"

  lambda_policy = {
    dynamodb_get = {
      actions = [ 
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.events_seriesId_eventId_DELETE.lambda_arn,
        module.events_seriesId_eventId_POST.lambda_arn,
        module.events_seriesId_eventId_PUT.lambda_arn
      ]
    }
  }
  
  lambda_env = {
    EVENT_SERIES_TABLE = aws_dynamodb_table.event_series_table.id

    EVENT_DELETE_LAMBDA = module.events_seriesId_eventId_DELETE.lambda_arn
    EVENT_POST_LAMBDA = module.events_seriesId_eventId_POST.lambda_arn
    EVENT_PUT_LAMBDA = module.events_seriesId_eventId_PUT.lambda_arn
  }
}

# /socials/{seriesId}/{eventId}/allocate

module "socials_seriesId_eventId_allocate" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.socials_seriesId_eventId.resource_id
  path_part   = "allocate"
}

module "socials_seriesId_eventId_allocate_PUT" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.socials_seriesId_eventId_allocate.resource_path

  http_method = "PUT"

  prefix = var.prefix
  name = "socials_seriesId_eventId_allocate"
  description = "Socials proxy"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/socials/{seriesId}/{eventId}/allocate/PUT"

  lambda_policy = {
    dynamodb_get = {
      actions = [ 
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.events_seriesId_eventId_allocate_PUT.lambda_arn
      ]
    }
  }
  
  lambda_env = {
    EVENT_SERIES_TABLE = aws_dynamodb_table.event_series_table.id

    EVENT_ALLOCATE_LAMBDA = module.events_seriesId_eventId_allocate_PUT.lambda_arn
  }
}


# /socials/{seriesId}/{eventId}/allocate/{id}

module "socials_seriesId_eventId_allocate_id" {
  source = "./api_resource"
  depends_on = [ aws_api_gateway_rest_api.portal ]

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.socials_seriesId_eventId_allocate.resource_id
  path_part   = "id"
}

module "socials_seriesId_eventId_allocate_id_DELETE" {
  source = "./api_method_lambda"
  depends_on = [ aws_api_gateway_rest_api.portal ]
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.socials_seriesId_eventId_allocate_id.resource_path

  http_method = "DELETE"

  prefix = var.prefix
  name = "socials_seriesId_eventId_allocate_id"
  description = "Socials proxy"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/socials/{seriesId}/{eventId}/allocate/{id}/DELETE"

  lambda_policy = {
    dynamodb_get = {
      actions = [ 
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.events_seriesId_eventId_allocate_id_DELETE.lambda_arn
      ]
    }
  }
  
  lambda_env = {
    EVENT_SERIES_TABLE = aws_dynamodb_table.event_series_table.id

    EVENT_ALLOCATE_LAMBDA = module.events_seriesId_eventId_allocate_id_DELETE.lambda_arn
  }
}