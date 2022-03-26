import boto3
from   boto3.dynamodb.conditions import Key
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_INSTANCE_TABLE_NAME = os.getenv('EVENT_INSTANCE_TABLE_NAME')
EVENT_SERIES_TABLE_NAME = os.getenv('EVENT_SERIES_TABLE_NAME')

logger.info(f"EVENT_INSTANCE_TABLE_NAME = {EVENT_INSTANCE_TABLE_NAME}")
logger.info(f"EVENT_SERIES_TABLE_NAME = {EVENT_SERIES_TABLE_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,DELETE",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE_NAME)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE_NAME)

def handler(event, context):
  logger.debug(event)

  eventSeriesId = str(event['pathParameters']['seriesId']).strip().lower()

  # Check the event series exists
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
      "headers": headers
    }

  # Check there are no instances using this event series
  try:
    response = event_instance_table.query(
      KeyConditionExpression=Key("eventSeriesId").eq(eventSeriesId),
      ProjectionExpression="eventSeriesId"
    )

    if "Items" in response and len(response["Items"]) > 0:
      return {
        "statusCode": 422,
        "headers": headers,
        "body": json.dumps({
          "message": f"Can't delete {eventSeriesId} because it currently has 1 or more event instances"
        })
      }
  except Exception as e:
    logger.error(f"Unable to get event instances from {EVENT_INSTANCE_TABLE_NAME}: {str(e)}")
    raise e
  
  # Delete event series
  logger.info(f"Deleting event series {eventSeriesId}")

  try:
    event_series_table.delete_item(
      Key={
        "eventSeriesId": eventSeriesId
      }
    )
  except Exception as e:
    logger.error(f"Unable to delete event series from {EVENT_SERIES_TABLE_NAME}: {str(e)}")
    raise e
  
  logger.info(f"Deleted event series {eventSeriesId}")

  return {
    "statusCode": 200,
    "headers": headers
  }