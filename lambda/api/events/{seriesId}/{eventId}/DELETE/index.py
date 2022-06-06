
import boto3
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')

logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)

def handler(event, context):
  event_series_id = event['pathParameters']['seriesId']
  event_id = event['pathParameters']['eventId']

  try:
    event_instance_table.delete_item(
      Key={
        "eventSeriesId": event_series_id,
        "eventId": event_id
      }
    )
  except Exception as e:
    logger.error(f"Unable to delete event instance (Event Series = {event_series_id}, Event ID = {event_id}) from {EVENT_INSTANCE_TABLE}: {str(e)}")
    raise e

  return {
    "statusCode": 204,
    "headers": headers
  }