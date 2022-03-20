
import boto3
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')

logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,DELETE",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)

def handler(event, context):
  event_series_id = event['pathParameters']['seriesId']
  event_id = event['pathParameters']['eventId']
  membership_number = event['pathParameters']['id']

  combined_id = event_series_id + "/" + event_id

  # Delete allocation
  try:
    event_allocations_table.delete_item(
      Key={
        "combinedEventId": combined_id,
        "membershipNumber": membership_number
      }
    )
  except Exception as e:
    logger.error(f"Unable to delete event allocation (Event Series = {event_series_id}, Event ID = {event_id}, Membership Number = {membership_number}) in {EVENT_ALLOCATIONS_TABLE}: {str(e)}")
    raise e

  logger.info(f"Deleted allocation of {membership_number} to event {combined_id}")

  return {
    "statusCode": 200,
    "headers": headers
  }