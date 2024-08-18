
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

import boto3
import datetime
import os

# Configure logging
logger = Logger()

ALLOCATIONS_TABLE = os.getenv('ALLOCATIONS_TABLE')
EVENT_ALLOCATIONS_INDEX = os.getenv('EVENT_ALLOCATIONS_INDEX')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')

logger.info("Initialising Lambda", extra={"environment_variables": {
  "ALLOCATIONS_TABLE": ALLOCATIONS_TABLE,
  "EVENT_ALLOCATIONS_INDEX": EVENT_ALLOCATIONS_INDEX,
  "EVENT_INSTANCE_TABLE": EVENT_INSTANCE_TABLE
}})

# Set up AWS
dynamodb = boto3.resource('dynamodb')
event_allocations_table = dynamodb.Table(ALLOCATIONS_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)

# Set up event cache
event_cache = dict()

def handler(event, context):
  membershipNumber = str(event['membershipNumber'])

  ret = dict()

  # List allocations
  try:
    allocations = event_allocations_table.query(
      IndexName=EVENT_ALLOCATIONS_INDEX,
      KeyConditionExpression="membershipNumber=:membershipNumber",
      ExpressionAttributeValues={
        ":membershipNumber": membershipNumber
      }
    )['Items']
  except Exception as e:
    logger.error(f"Unable to get allocations for member {membershipNumber}: {str(e)}")
    raise e
  
  # Check each allocation
  future = datetime.date.today().isoformat()

  for allocation in allocations:
    combinedEventId = allocation['combinedEventId']

    if combinedEventId not in event_cache:
      series, instance = allocation['combinedEventId'].split("/", 1)

      try:
        i = event_instance_table.get_item(Key={'eventSeriesId': series, 'eventId': instance}, ProjectionExpression="eventSeriesId,eventId,startDate")['Item']
      except Exception as e:
        logger.error(f"Unable to get event details for {series}/{instance}: {str(e)}")
        continue

      event_cache[combinedEventId] = i

    event = event_cache[combinedEventId]

    if event["startDate"] >= future:
      ret[combinedEventId] = allocation.get("allocation")

  return ret