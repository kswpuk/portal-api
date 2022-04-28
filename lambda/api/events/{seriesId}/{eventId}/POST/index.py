import boto3
from decimal import Decimal
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_INSTANCE_TABLE_NAME = os.getenv('EVENT_INSTANCE_TABLE_NAME')
VALIDATION_ARN = os.getenv('VALIDATION_ARN')

logger.info(f"EVENT_INSTANCE_TABLE_NAME = {EVENT_INSTANCE_TABLE_NAME}")
logger.info(f"VALIDATION_ARN = {VALIDATION_ARN}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,POST",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE_NAME)
lambda_client = boto3.client('lambda')

def handler(event, context):
  logger.debug(event)

  eventSeriesId = str(event['pathParameters']['seriesId']).strip().lower()
  eventId = str(event['pathParameters']['eventId']).strip().lower()

  # Check that the instance ID doesn't exist
  logger.debug(f"Checking event instance {eventSeriesId}/{eventId} doesn't already exist")
  try:
    response = event_instance_table.get_item(
      Key={
        "eventSeriesId": eventSeriesId,
        "eventId": eventId,
      },
      AttributesToGet=[
        "eventSeriesId,eventId"
      ]
    )
    if 'Item' in response and 'eventId' in response['Item']:
      return {
        "statusCode": 422,
        "headers": headers,
        "body": json.dumps({
          "message": f"Event {eventSeriesId}/{eventId} already exists"
        })
      }
  except Exception as e:
    logger.error(f"Unable to check if {eventSeriesId}/{eventId} exists: {str(e)}")
    raise e

  # Do validation
  logger.debug(f"Validating input for {eventSeriesId}/{eventId}...")

  instance = json.loads(event['body'])
  instance["eventSeriesId"] = eventSeriesId
  instance["eventId"] = eventId

  try:
    validationResult = json.loads(lambda_client.invoke(
      FunctionName=VALIDATION_ARN,
      Payload=json.dumps(instance)
    )['Payload'].read())
  except Exception as e:
    logger.error(f"Unable to validate event {eventSeriesId}/{eventId}: {str(e)}")
    raise e

  if not validationResult["valid"]:
    logger.warning(f"{len(validationResult['errors'])} errors found during validation of event {eventSeriesId}/{eventId}: {validationResult['errors']}")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "Errors found during validation",
        "detail": validationResult['errors']
      })
    }
  else:
    logger.info(f"No errors found during validation of event {eventSeriesId}/{eventId}")

  # Put records in DynamoDB
  logger.debug(f"Creating event {eventSeriesId}/{eventId}...")

  response = event_instance_table.put_item(
    Item={
      **validationResult["event"],
      "cost": Decimal(str(validationResult["event"].get("cost", 0.00))).quantize(Decimal('.01'))
    },
    ReturnValues = "NONE"
  )

  logger.debug(f"Server response: {response}")
  logger.info(f"Event {eventSeriesId}/{eventId} created")

  return {
    "statusCode": 200,
    "headers": headers
  }