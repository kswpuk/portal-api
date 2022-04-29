
import boto3
from   boto3.dynamodb.conditions import Key, Attr
import json
import logging
import numpy as np
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
WEIGHTING_ARN = os.getenv('WEIGHTING_ARN')

logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"WEIGHTING_ARN = {WEIGHTING_ARN}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,DELETE",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')
event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)

lambda_client = boto3.client('lambda')

def handler(event, context):
  event_series_id = event['pathParameters']['seriesId']
  event_id = event['pathParameters']['eventId']

  # Get allocations
  combined_event_id = event_series_id + "/" + event_id
  allocations = get_allocations(combined_event_id)

  registered_allocations = list(filter(lambda a: a["allocation"] == "REGISTERED", allocations))

  # Get event
  try:
    instance = event_instance_table.get_item(
      Key={
        "eventSeriesId": event_series_id,
        "eventId": event_id
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event instance {event_series_id}/{event_id} from {EVENT_INSTANCE_TABLE}: {str(e)}")
    raise e

  # Get rules
  rules = instance.get("weightingCriteria", None)
  if type(rules) is not dict or len(rules.keys()) == 0:
    rules = None

  # If limit is provided use that, otherwise calculate from event
  if 'queryStringParameters' in event and event['queryStringParameters'] is not None and 'limit' in event['queryStringParameters']:
    attendanceLimit = int(event["queryStringParameters"]["limit"])
  else:
    allocated_allocations = list(filter(lambda a: a["allocation"] == "ALLOCATED", allocations))
    logger.debug(f"Existing allocations = {len(allocated_allocations)}")

    attendanceLimit = int(instance["attendanceLimit"]) - len(allocated_allocations)

  # Print information about event
  logger.info(f"Attendance limit = {attendanceLimit}")
  logger.info(f"Allocation weighting = {rules}")

  # Check we need to do allocations
  if attendanceLimit == 0 or len(registered_allocations) <= attendanceLimit or len(registered_allocations) == 0:
    return {
      "statusCode": 200,
      "headers": headers,
      "body": json.dumps(list(map(lambda a: a["membershipNumber"], registered_allocations)))
    }

  # If no weighting, then just randomly allocate
  if rules is None:
    selected = np.random.choice(list(weightings.keys()), attendanceLimit, replace=False)
  
  # Otherwise apply the rules
  else:
    weightings = {}
    matches = {}

    # Calculate initial weighting for each member
    for allocation in registered_allocations:
      membership_number = allocation['membershipNumber']

      # Get weightings for each member
      try:
        w = json.loads(lambda_client.invoke(
          FunctionName=WEIGHTING_ARN,
          Payload=json.dumps({
            "eventSeriesId": event_series_id,
            "eventId": event_id,
            "membershipNumber": membership_number
          })
        )['Payload'].read())

        if 'errorType' in w:
          logger.error(f"Lambda failed to calculate member {membership_number}'s weighting for event {event_series_id}/{event_id}: {w['errorType']} ({w.get('errorMessage')})")
        else:
          matches[membership_number] = w['weightings']
          weightings[membership_number] = 0
      except Exception as e:
        logger.error(f"Unable to invoke Lambda to calculate member {membership_number}'s weighting for event {event_series_id}/{event_id}: {str(e)}")
        raise e

    # Catch the case where we've not been able to calculate weightings for all
    if len(weightings) <= attendanceLimit or len(weightings) == 0:
      return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps(list(weightings.keys()))
      }

    # Get initial weighintgs
    for k, v in rules.items():
      for membership_number in matches:
        weightings[membership_number] += v*matches[membership_number].get(k, 0)

    # Shift counts so all are above 0
    min_val = min(weightings.values())
    if min_val < 1:
      offset = -min_val + 1
      for membership_number in weightings:
        weightings[membership_number] += offset

    # Normalize so values sum to 1
    sum_val = sum(weightings.values())
    for membership_number in weightings:
      weightings[membership_number] /= sum_val
    
    # Weighted sample to get suggested allocations up to limit
    selected = np.random.choice(list(weightings.keys()), attendanceLimit, replace=False, p=list(weightings.values()))

  # Return results
  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(selected.tolist())
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
