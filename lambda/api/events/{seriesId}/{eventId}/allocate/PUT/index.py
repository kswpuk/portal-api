
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
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)

def handler(event, context):
  event_series_id = event['pathParameters']['seriesId']
  event_id = event['pathParameters']['eventId']
  
  combined_id = event_series_id + "/" + event_id

  body = json.loads(event['body'])

  for a in body.get("allocations", []):
    allocation = a.get("allocation")
    if allocation is None:
      logger.warn(f"No allocation provided in {a}")
      continue

    membership_numbers = a.get("membershipNumbers", [])

    for m in membership_numbers:
      # Update allocation
      try:
        event_allocations_table.update_item(
          Key={
            "combinedEventId": combined_id,
            "membershipNumber": m
          },
          UpdateExpression="SET allocation = :v",
          ExpressionAttributeValues={
            ":v": allocation
          },
          ReturnValues="ALL_NEW"
        )
      except Exception as e:
        logger.error(f"Unable to update event allocation (Event Series = {event_series_id}, Event ID = {event_id}, Membership Number = {m}) in {EVENT_ALLOCATIONS_TABLE}: {str(e)}")
        raise e

      logger.info(f"Set allocation to {allocation} for {m} on event {combined_id}")

  return {
    "statusCode": 200,
    "headers": headers
  }