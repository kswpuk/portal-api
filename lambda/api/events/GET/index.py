
import boto3
from   boto3.dynamodb.conditions import Attr
import datetime
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')

logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")

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

def handler(event, context):
  all = 'queryStringParameters' in event and event['queryStringParameters'] is not None and 'all' in event['queryStringParameters']
  now = datetime.datetime.now().replace(microsecond=0)

  if 'requestContext' in event and 'authorizer' in event['requestContext'] and 'membershipNumber' in event['requestContext']['authorizer']:
    membershipNumber = event['requestContext']['authorizer']['membershipNumber']
  else:
    membershipNumber = None
  
  logger.debug(f"Membership number for requestor: {membershipNumber}")

  try:
    if all:
      logger.debug("Scanning for all event instances")
      instances = scan_events()
    else:
      logger.debug(f"Scanning for event instances that finish after {now.isoformat()}")

      # TODO: Make this more effective?
      instances = scan_events(
        FilterExpression=Attr('endDate').gt(now.isoformat())
      )
  except Exception as e:
    logger.error(f"Unable to get event instances from {EVENT_INSTANCE_TABLE}: {str(e)}")
    raise e
  
  results = []

  series = {}
  for instance in instances:
    # Get series details
    if instance['eventSeriesId'] not in series:
      try:
        event_series = event_series_table.get_item(
          Key={
            "eventSeriesId": instance['eventSeriesId']
          }
        )

        if 'Item' in event_series:
          event_series = event_series['Item']
        else:
          event_series = {}

        series[instance['eventSeriesId']] = event_series
      except Exception as e:
        logger.error(f"Unable to get event series from {EVENT_SERIES_TABLE} for eventSeriesId {instance['eventSeriesId']}: {str(e)}")
        event_series = {}
    else:
      event_series = series.get(instance['eventSeriesId'])
    
    # Get allocations
    allocation = {}
    combinedEventId = instance['eventSeriesId'] + "/" + instance['eventId']

    if membershipNumber:
      try:
        allocation_response = event_allocations_table.get_item(
          Key={
            "combinedEventId": combinedEventId,
            "membershipNumber": membershipNumber
          }
        )
        if 'Item' in allocation_response:
          allocation = allocation_response['Item']

      except Exception as e:
        logger.error(f"Unable to get event allocation information from {EVENT_ALLOCATIONS_TABLE} for combinedEventId {combinedEventId} for member {membershipNumber}: {str(e)}")
    
    start_date = datetime.datetime.fromisoformat(instance['startDate'])
    end_date = datetime.datetime.fromisoformat(instance['endDate'])

    additional = {
      "live": start_date < now and end_date > now,
      "past": end_date < now,
      "allocation": allocation.get('allocation'),
      "combinedEventId": combinedEventId
    }

    results.append(instance | event_series | additional)

  results = sorted(results, key=lambda d: (d['startDate'], d['name']), reverse=True) 

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(results)
  }


def scan_events(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = event_instance_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        **kwargs
      )
    else: 
      response = event_instance_table.scan(**kwargs)

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results
