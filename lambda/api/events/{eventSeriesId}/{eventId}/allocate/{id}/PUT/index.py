
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
  event_series_id = event['pathParameters']['eventSeriesId']
  event_id = event['pathParameters']['eventId']
  membership_number = event['pathParameters']['id']

  allocation = json.loads(event['body']).get("allocation")
  combined_id = event_series_id + "/" + event_id

  if allocation is None:
    return {
      "statusCode": 400,
      "headers": headers,
      "body": json.dumps({
        "message": "No allocation provided"
      })
    }

  # Update allocation
  try:
    new_allocation = event_allocations_table.update_item(
      Key={
        "combinedEventId": combined_id,
        "membershipNumber": membership_number
      },
      UpdateExpression="SET allocation = :v",
      ExpressionAttributeValues={
        ":v": allocation
      },
      ReturnValues="ALL_NEW"
    )['Attributes']
  except Exception as e:
    logger.error(f"Unable to update event allocation (Event Series = {event_series_id}, Event ID = {event_id}, Membership Number = {membership_number}) in {EVENT_ALLOCATIONS_TABLE}: {str(e)}")
    raise e

  logger.info(f"Set allocation to {allocation} for {membership_number} on event {combined_id}")

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(new_allocation)
  }