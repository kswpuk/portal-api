import boto3
from decimal import Decimal
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATE_LAMBDA = os.getenv('EVENT_ALLOCATE_LAMBDA')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')

logger.info(f"EVENT_ALLOCATE_LAMBDA = {EVENT_ALLOCATE_LAMBDA}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,POST",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)

lambda_client = boto3.client('lambda')

def handler(event, context):
  logger.debug(event)

  eventSeriesId = str(event['pathParameters']['seriesId']).strip().lower()

  # Get series information
  logger.debug(f"Getting event series information for {eventSeriesId}")
  try:
    series = event_series_table.get_item(
      Key={
        "eventSeriesId": eventSeriesId
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event series {eventSeriesId}: {str(e)}")
    raise e

  if series["type"] != "social":
    return {
      "statusCode": 403,
      "headers": headers,
      "body": json.dumps({
        "message": f"You do not have permission to modify a non-social event"
      })
    }

  try:
    return json.loads(lambda_client.invoke(
      FunctionName=EVENT_ALLOCATE_LAMBDA,
      Payload=json.dumps(event)
    )['Payload'].read())
  except Exception as e:
    logger.error(f"Failed to invoked Lambda {EVENT_ALLOCATE_LAMBDA}: {str(e)}")
    raise e