import boto3
from   boto3.dynamodb.conditions import Attr
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_INDEX = os.getenv('EVENT_ALLOCATIONS_INDEX')
EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"EVENT_ALLOCATIONS_INDEX = {EVENT_ALLOCATIONS_INDEX}")
logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,POST",
  "Access-Control-Allow-Origin": "*"
}

# TODO: Can we avoid Cognito creating a new account, and instead reuse the existing one?

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)
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
  
  # Check membership number isn't current member
  try:
    requestor = int(event['requestContext']['authorizer']['membershipNumber'])
  except:
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get membership number of requestor"
    }
  
  if requestor == membershipNumber:
    return {
      "statusCode": 403,
      "headers": headers,
      "body": "Can't update your own membership number"
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
  
  logger.info("Validating input")

  try:
    newMembershipNumber = int(json.loads(event['body'])['membershipNumber'])
  except:
    logger.error(f"Unable to parse new membership number: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to parse new membership number"
    }
  
  if newMembershipNumber <= 0:
    logger.error(f"Membership number {newMembershipNumber} must be positive")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": "Membership number must be positive"
    }
  
  logger.info(f"Confirming member {newMembershipNumber} does not already exist")

  try:
    member = members_table.get_item(Key={'membershipNumber': newMembershipNumber}, ProjectionExpression="membershipNumber")['Item']

    logger.error(f"Member {newMembershipNumber} already exists: {str(e)}")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": "Member already exists"
    }
  except Exception as e:
    # Do nothing - we want this to fail as the member shouldn't already exist

  logger.info(f"Getting event allocations for member {membershipNumber}")
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

  logger.info(f"Updating membership number for member {membershipNumber} to {newMembershipNumber}")
  
  # Update (delete and recreate) membership table
  logger.info(f"Updating membership table for member {membershipNumber}")
  replace_dynamodb_item(members_table, {'membershipNumber': membershipNumber}, {'membershipNumber': newMembershipNumber})

  # Update (delete and recreate) event allocations
  logger.info(f"Updating event allocations table for member {membershipNumber}")
  for allocation in allocations:
    logger.debug(f"Updating membership number for event {allocation['combinedEventId']}")
    replace_dynamodb_item(event_allocations_table, {'combinedEventId': allocation['combinedEventId'], 'membershipNumber': membershipNumber}, {'combinedEventId': allocation['combinedEventId'], 'membershipNumber': newMembershipNumber})

  logger.info(f"Successfully updated membership number for member {membershipNumber} to {newMembershipNumber}")

  return {
    "statusCode": 204,
    "headers": headers
  }

def replace_dynamodb_item(table, key, new_key):
  curr = table.get_item(Key=key)['Item']
  # TODO: Delete item
  
  new_item = curr | new_key

  table.put_item(
    Item=new_item,
    ReturnValues = "NONE"
  )
