import boto3
from decimal import Decimal
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_DELETE_LAMBDA = os.getenv('EVENT_DELETE_LAMBDA')
EVENT_POST_LAMBDA = os.getenv('EVENT_POST_LAMBDA')
EVENT_PUT_LAMBDA = os.getenv('EVENT_PUT_LAMBDA')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')

logger.info(f"EVENT_DELETE_LAMBDA = {EVENT_DELETE_LAMBDA}")
logger.info(f"EVENT_POST_LAMBDA = {EVENT_POST_LAMBDA}")
logger.info(f"EVENT_PUT_LAMBDA = {EVENT_PUT_LAMBDA}")
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

  method = event['httpMethod']
  lambda_arn = None
  
  if method == "DELETE":
    lambda_arn = EVENT_DELETE_LAMBDA
  if method == "POST":
    lambda_arn = EVENT_POST_LAMBDA
  elif method == "PUT":
    lambda_arn = EVENT_PUT_LAMBDA
  
  if lambda_arn is not None:
    try:
      return json.loads(lambda_client.invoke(
        FunctionName=lambda_arn,
        Payload=json.dumps(event)
      )['Payload'].read())
    except Exception as e:
      logger.error(f"Failed to invoked Lambda {lambda_arn}: {str(e)}")
      raise e

  return {
    "statusCode": 405,
    "headers": headers,
    "body": json.dumps({
      "message": f"Method {method} not supported"
    })
  }

  # TODO: Add allocation integration too