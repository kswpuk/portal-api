
import boto3
from   boto3.dynamodb.conditions import Key, Attr
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

ELIGIBILITY_ARN = os.getenv('ELIGIBILITY_ARN')
EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"ELIGIBILITY_ARN = {ELIGIBILITY_ARN}")
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
lambda_client = boto3.client('lambda')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):
  event_series_id = event['pathParameters']['seriesId']
  event_id = event['pathParameters']['eventId']

  membership_number = event['requestContext']['authorizer']['membershipNumber']
  
  try:
    event_series = event_series_table.get_item(
      Key={
        "eventSeriesId": event_series_id
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event series (Event Series = {event_series_id}) from {EVENT_SERIES_TABLE}: {str(e)}")
    raise e

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
  
  # Convert decimal to int in instance["weightingCriteria"]
  if "weightingCriteria" in instance and type(instance["weightingCriteria"]) is dict:
    weightings = {}
    for k, v in instance["weightingCriteria"].items():
      weightings[k] = int(v)
    
    instance["weightingCriteria"] = weightings
  
  try:
    allocations = get_allocations(event_series_id + "/" + event_id)
  except Exception as e:
    logger.error(f"Unable to get event allocations (Event Series = {event_series_id}, Event ID = {event_id}) from {EVENT_ALLOCATIONS_TABLE}: {str(e)}")
    raise e
  
  enh_allocations = []
  for allocation in allocations:
    member = {}
    try:
      member = members_table.get_item(
        Key={
          "membershipNumber": allocation['membershipNumber']
        },
        ProjectionExpression="membershipNumber,firstName,preferredName,surname,receivedNecker"
      )['Item']
      
    except Exception as e:
      logger.error(f"Unable to get member details for {allocation['membershipNumber']} from {MEMBERS_TABLE}: {str(e)}")
      # Don't raise, just continue
    
    enh_allocations.append({
      "membershipNumber": allocation['membershipNumber'],
      "allocation": allocation['allocation']
    } | member)
  
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

  combined = instance | event_series | {"allocations": enh_allocations, "eligibility": eligible}

  if combined.get("attendanceLimit") is not None:
    combined["attendanceLimit"] = int(combined["attendanceLimit"])
  
  if combined.get("cost") is not None:
    combined["cost"] = float(combined["cost"])

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(combined)
  }

def get_allocations(combined_event_id):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = event_allocations_table.query(
        KeyConditionExpression=Key("combinedEventId").eq(combined_event_id),
        ExclusiveStartKey=last_evaluated_key,
        FilterExpression=Attr("allocation").ne("UNREGISTERED")
      )
    else: 
      response = event_allocations_table.query(
        KeyConditionExpression=Key("combinedEventId").eq(combined_event_id),
        FilterExpression=Attr("allocation").ne("UNREGISTERED")
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results
