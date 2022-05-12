import boto3
import json
import logging
import os
import re

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_SERIES_TABLE_NAME = os.getenv('EVENT_SERIES_TABLE_NAME')
logger.info(f"EVENT_SERIES_TABLE_NAME = {EVENT_SERIES_TABLE_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE_NAME)

def handler(event, context):
  logger.debug(event)

  eventSeriesId = str(event['pathParameters']['seriesId']).strip().lower()

  # Check this ID exists!

  logger.debug(f"Confirming {eventSeriesId} exists")

  response = event_series_table.get_item(
    Key={
      "eventSeriesId": eventSeriesId
    },
    AttributesToGet=[
      "eventSeriesId"
    ]
  )
  if 'Item' not in response or 'eventSeriesId' not in response['Item']:
    return {
      "statusCode": 404,
      "headers": headers,
    }

  # Do validation

  logger.info(f"Validating input for {eventSeriesId}...")

  validationErrors = []
  series = json.loads(event['body'])

  name = str(series.get("name", "")).strip()
  if name == "":
    validationErrors.append("Event name cannot be empty")
  
  description = str(series.get("description", "")).strip()
  if description == "":
    validationErrors.append("Description cannot be empty")

  eventType = str(series.get("type")).strip()
  if eventType not in ["event", "social", "no_impact"]:
    validationErrors.append("Event type must be a supported value")

  if len(validationErrors) > 0:
    logger.warning(f"{len(validationErrors)} errors found during validation of event series {eventSeriesId}: {validationErrors}")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "Errors found during validation",
        "detail": validationErrors
      })
    }
  else:
    logger.info(f"No errors found during validation of event series {eventSeriesId}")

  # Update records in DynamoDB
  logger.debug(f"Updating event series {eventSeriesId}...")

  response = event_series_table.update_item(
    Key={
      "eventSeriesId": eventSeriesId
    },
    UpdateExpression = "SET #n=:name, description=:description, #t=:type",
    ExpressionAttributeNames={
      "#n": "name",
      "#t": "type"
    },
    ExpressionAttributeValues={
      ":name": name,
      ":description": description,
      ":type": eventType
    },
    ReturnValues = "NONE"
  )

  logger.debug(f"Server response: {response}")
  logger.info(f"Event series updated for {eventSeriesId}")

  return {
    "statusCode": 200,
    "headers": headers
  }