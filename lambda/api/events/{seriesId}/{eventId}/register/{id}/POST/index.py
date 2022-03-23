
import boto3
import datetime
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

ELIGIBILITY_ARN = os.getenv('ELIGIBILITY_ARN')
EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')

logger.info(f"ELIGIBILITY_ARN = {ELIGIBILITY_ARN}")
logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,POST",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)

def handler(event, context):
  event_series_id = event['pathParameters']['seriesId']
  event_id = event['pathParameters']['eventId']
  membership_number = event['pathParameters']['id']

  combined_id = event_series_id + "/" + event_id
  today = datetime.date.today()

  # Get event instance
  try:
    instance = event_instance_table.get_item(
      Key={
        "eventSeriesId": event_series_id,
        "eventId": event_id
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event instance (Event Series = {event_series_id}, Event ID = {event_id}) from {EVENT_INSTANCE_TABLE}: {str(e)}")
    raise e

  # Check registration is still possible
  deadline = datetime.date.fromisoformat(instance['registrationDate'])
  if deadline < today:
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "Registration deadline has already passed"
      })
    }

  # Check current allocation status is either none or REGISTERED
  try:
    current_allocation = event_allocations_table.get_item(
      Key={
        "combinedEventId": combined_id,
        "membershipNumber": membership_number
      }
    )['Item']

    current_status = current_allocation["allocation"]
  except Exception as e:
    current_status = "UNREGISTERED"
  
  if current_status == "REGISTERED":
    # Delete 
    try:
      event_allocations_table.delete_item(
        Key={
          "combinedEventId": combined_id,
          "membershipNumber": membership_number
        }
      )['Attributes']
    except Exception as e:
      logger.error(f"Unable to update event allocation (Event Series = {event_series_id}, Event ID = {event_id}, Membership Number = {membership_number}) in {EVENT_ALLOCATIONS_TABLE}: {str(e)}")
      raise e
    
    logger.info(f"{membership_number} unregistered from event {combined_id}")
    
    return {
      "statusCode": 200,
      "headers": headers
    }
    
  elif current_status == "UNREGISTERED":
    # Check applicant meets eligibility criteria
    try:
      eligible = json.loads(lambda_client.invoke(
        FunctionName=ELIGIBILITY_ARN,
        Payload=json.dumps({
          "eventSeriesId": event_series_id,
          "eventId": event_id,
          "membershipNumber": membership_number
        })
      )['Payload'].read())
    except Exception as e:
      logger.error(f"Unable to confirm event {event_series_id}/{event_id} eligibility for {membership_number}: {str(e)}")
      raise e

    if not eligible.get("eligible"):
      return {
        "statusCode": 422,
        "headers": headers,
        "body": json.dumps({
          "message": "Eligibility criteria not met"
        })
      }

    # Register
    try:
      new_allocation = event_allocations_table.update_item(
        Key={
          "combinedEventId": combined_id,
          "membershipNumber": membership_number
        },
        UpdateExpression="SET allocation = :v",
        ExpressionAttributeValues={
          ":v": "REGISTERED"
        },
        ReturnValues="ALL_NEW"
      )['Attributes']
    except Exception as e:
      logger.error(f"Unable to register for event (Event Series = {event_series_id}, Event ID = {event_id}, Membership Number = {membership_number}) in {EVENT_ALLOCATIONS_TABLE}: {str(e)}")
      raise e
    
    logger.info(f"{membership_number} registered for event {combined_id}")
    
    return {
      "statusCode": 200,
      "headers": headers,
      "body": json.dumps(new_allocation)
    }

  else:
    return {
      "statusCode": 403,
      "headers": headers,
      "body": json.dumps({
        "message": f"Not authorized to change existing allocation status of {current_status}"
      })
    }
  