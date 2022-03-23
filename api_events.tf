# /events

module "events" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = aws_api_gateway_rest_api.portal.root_resource_id
  path_part   = "events"
}

module "events_GET" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.events.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "events"
  description = "List events"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/GET"

  lambda_policy = {
    dynamodb = {
      actions = [ 
        "dynamodb:GetItem",
        "dynamodb:Scan"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn,
        aws_dynamodb_table.event_instance_table.arn,
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }
  }
  
  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE = aws_dynamodb_table.event_series_table.id
  }
}

# /events/{seriesId}

module "events_seriesId" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events.resource_id
  path_part   = "{seriesId}"
}

# /events/{seriesId}/{eventId}

module "events_seriesId_eventId" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId.resource_id
  path_part   = "{eventId}"
}

module "events_seriesId_eventId_GET" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.events_seriesId_eventId.resource_path

  http_method   = "GET"

  prefix = var.prefix
  name = "events_seriesId_eventId"
  description = "Get event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/GET"

  lambda_policy = {
    dynamodb_get = {
      actions = [ 
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_series_table.arn,
        aws_dynamodb_table.event_instance_table.arn,
        aws_dynamodb_table.members_table.arn
      ]
    }

    dynamodb_query = {
      actions = [ 
        "dynamodb:Query"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_events_eligible.lambda_function_arn
      ]
    }
  }
  
  lambda_env = {
    ELIGIBILITY_ARN = module.utils_events_eligible.lambda_function_arn
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.id
    EVENT_SERIES_TABLE = aws_dynamodb_table.event_series_table.id
    MEMBERS_TABLE = aws_dynamodb_table.members_table.id
  }
}

# /events/{seriesId}/{eventId}/allocate

module "events_seriesId_eventId_allocate" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId.resource_id
  path_part   = "allocate"
}


module "events_seriesId_eventId_allocate_PUT" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.events_seriesId_eventId_allocate.resource_path

  http_method   = "PUT"

  prefix = var.prefix
  name = "events_seriesId_eventId_allocate"
  description = "Allocate member to event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/allocate/PUT"

  lambda_policy = {
    dynamodb_allocation = {
      actions = [ 
        "dynamodb:UpdateItem"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }
  }
  
  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
  }
}

# /events/{seriesId}/{eventId}/allocate/{id}

module "events_seriesId_eventId_allocate_id" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId_allocate.resource_id
  path_part   = "{id}"
}

module "events_seriesId_eventId_allocate_id_DELETE" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.events_seriesId_eventId_allocate_id.resource_path

  http_method   = "DELETE"

  prefix = var.prefix
  name = "events_seriesId_eventId_allocate_id"
  description = "Delete allocation"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/allocate/{id}/DELETE"

  lambda_policy = {
    dynamodb_allocation = {
      actions = [ 
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }
  }
  
  lambda_env = {
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
  }
}

# /events/{seriesId}/{eventId}/register

module "events_seriesId_eventId_register" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId.resource_id
  path_part   = "register"
}

# /events/{seriesId}/{eventId}/register/{id}

module "events_seriesId_eventId_register_id" {
  source = "./api_resource"

  rest_api_id = aws_api_gateway_rest_api.portal.id
  parent_id   = module.events_seriesId_eventId_register.resource_id
  path_part   = "{id}"
}

module "events_seriesId_eventId_register_id_POST" {
  source = "./api_method_lambda"
  
  rest_api_name = aws_api_gateway_rest_api.portal.name
  path = module.events_seriesId_eventId_register_id.resource_path

  http_method   = "POST"

  prefix = var.prefix
  name = "events_seriesId_eventId_register_id"
  description = "Register for event"

  authorizer_id = aws_api_gateway_authorizer.portal.id

  lambda_path = "${path.module}/lambda/api/events/{seriesId}/{eventId}/register/{id}/POST"

  lambda_policy = {
    dynamodb_event = {
      actions = [ 
        "dynamodb:GetItem"
      ]
      resources = [
        aws_dynamodb_table.event_instance_table.arn
      ]
    }

    dynamodb_allocation = {
      actions = [ 
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ]
      resources = [
        aws_dynamodb_table.event_allocation_table.arn
      ]
    }

    lambda = {
      actions = [
        "lambda:InvokeFunction"
      ]
      resources = [
        module.utils_events_eligible.lambda_function_arn
      ]
    }
  }
  
  lambda_env = {
    ELIGIBILITY_ARN = module.utils_events_eligible.lambda_function_arn
    EVENT_ALLOCATIONS_TABLE = aws_dynamodb_table.event_allocation_table.id
    EVENT_INSTANCE_TABLE = aws_dynamodb_table.event_instance_table.id
  }
}