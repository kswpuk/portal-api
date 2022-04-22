
import boto3
from   boto3.dynamodb.conditions import Attr
import datetime
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_INDEX = os.getenv('EVENT_ALLOCATIONS_INDEX')
EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"EVENT_ALLOCATIONS_INDEX = {EVENT_ALLOCATIONS_INDEX}")
logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

event_names = {}

def handler(event, context):
  membershipNumber = event['pathParameters']['id']

  if membershipNumber is None:
    logger.warn("Unable to get membership number from path")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get membership number from path"
    }

  logger.info(f"Confirming member {membershipNumber} exists")

  try:
    member = members_table.get_item(Key={'membershipNumber': membershipNumber}, ProjectionExpression="membershipNumber")['Item']
  except Exception as e:
    logger.error(f"Unable to confirm member {membershipNumber} exists: {str(e)}")
    return {
      "statusCode": 404,
      "headers": headers,
      "body": "Member doesn't exist"
    }

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
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Couldn't get allocations"
    }

  # Get event details
  
  ret = []
  for allocation in allocations:
    series, instance = allocation['combinedEventId'].split("/", 1)

    if series not in event_names:
      try:
        s = event_series_table.get_item(
          Key={'eventSeriesId': series},
          ProjectionExpression="eventSeriesId,#n",
          ExpressionAttributeNames={
            "#n": "name"
          }
        )['Item']
        event_names[series] = s['name']
      except Exception as e:
        logger.error(f"Unable to get event name for {series}: {str(e)}")
        return {
          "statusCode": 500,
          "headers": headers,
          "body": "Couldn't get event name"
        }

    try:
      i = event_instance_table.get_item(Key={'eventSeriesId': series, 'eventId': instance}, ProjectionExpression="eventSeriesId,eventId,startDate")['Item']
    except Exception as e:
      logger.error(f"Unable to get event details for {series}/{instance}: {str(e)}")
      return {
        "statusCode": 500,
        "headers": headers,
        "body": "Couldn't get event details"
      }
    
    ret.append({
      **allocation,
      "name": event_names.get(series, "Unknown"),
      "startDate": i['startDate']
    })
  
  # Sort by date
  ret.sort(key=lambda x: x['startDate'], reverse=True)

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(ret)
  }