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
  "Access-Control-Allow-Methods": "OPTIONS,POST",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE_NAME)

def handler(event, context):
  logger.debug(event)

  eventSeriesId = str(event['pathParameters']['seriesId']).strip().lower()

  # Check this ID isn't already in use!

  logger.debug(f"Confirming {eventSeriesId} has not previously been used")

  response = event_series_table.get_item(
    Key={
      "eventSeriesId": eventSeriesId
    },
    AttributesToGet=[
      "eventSeriesId"
    ]
  )
  if 'Item' in response and 'eventSeriesId' in response['Item']:
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": f"Event series ID {eventSeriesId} has already been used"
      })
    }

  # Do validation

  logger.info(f"Validating input for {eventSeriesId}...")

  validationErrors = []
  series = json.loads(event['body'])

  if len(eventSeriesId) > 20:
    validationErrors.append("Event series ID cannot be longer than 20 characters")
  
  if not re.match("^[a-z][-a-z0-9]{,19}$", eventSeriesId):
    validationErrors.append("Event series ID must start with a letter, and can only contain lower case characters, numbers and hyphens")

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

  # Put records in DynamoDB
  logger.debug(f"Creating event series {eventSeriesId}...")

  response = event_series_table.put_item(
    Item={
      "eventSeriesId": eventSeriesId,
      "name": name,
      "description": description,
      "type": eventType
    },
    ConditionExpression = "attribute_not_exists(eventSeriesId)",
    ReturnValues = "NONE"
  )

  logger.debug(f"Server response: {response}")
  logger.info(f"Event series created for {eventSeriesId}")

  return {
    "statusCode": 200,
    "headers": headers
  }