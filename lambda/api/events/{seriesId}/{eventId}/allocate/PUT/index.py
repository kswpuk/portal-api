
import boto3
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
SUSPENDED_ARN = os.getenv('SUSPENDED_ARN')

logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"SUSPENDED_ARN = {SUSPENDED_ARN}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)

lambda_client = boto3.client('lambda')

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

    membership_numbers = [m for m in a.get("membershipNumbers", []) if not is_suspended(m)]

    logger.info(f"Updating event allocation for {len(membership_numbers)} non-suspended members")

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

def is_suspended(membership_number):
  try:
    suspended = json.loads(lambda_client.invoke(
      FunctionName=SUSPENDED_ARN,
      Payload=json.dumps({"membershipNumbers": [membership_number]})
    )['Payload'].read())
  except Exception as e:
    logger.error(f"Unable to get suspension status of member: {str(e)}")
    raise e
  
  return suspended.get(a["membershipNumber"], False)