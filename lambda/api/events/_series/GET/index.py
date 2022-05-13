
import boto3
from   boto3.dynamodb.conditions import Attr
from   collections import defaultdict
import datetime
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')

logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)

def handler(event, context):
  detailed = 'queryStringParameters' in event and event['queryStringParameters'] is not None and 'detailed' in event['queryStringParameters']

  try:
    series = scan_event_series()
  except Exception as e:
    logger.error(f"Unable to get event series from {EVENT_SERIES_TABLE}: {str(e)}")
    raise e

  series = sorted(series, key=lambda d: (d['name'])) 

  if detailed:
    try:
      instances = scan_event_instances()
    except Exception as e:
      logger.error(f"Unable to get event instances from {EVENT_INSTANCE_TABLE}: {str(e)}")
      raise e
    
    grouped_instances = defaultdict(list)
    
    for instance in instances:
      grouped_instances[instance["eventSeriesId"]].append(instance)
    
    for s in series:
      s["instances"] = sorted(grouped_instances[s["eventSeriesId"]], key=lambda d: (d['startDate']), reverse=True)
  
  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(series)
  }

def scan_event_series():
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = event_series_table.scan(
        ExclusiveStartKey=last_evaluated_key
      )
    else: 
      response = event_series_table.scan()

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results

def scan_event_instances():
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = event_instance_table.scan(
        ProjectionExpression="eventSeriesId,eventId,endDate,#l,locationType,postcode,startDate,#u",
        ExpressionAttributeNames={
          "#l": "location",
          "#u": "url"
        },
        ExclusiveStartKey=last_evaluated_key
      )
    else: 
      response = event_instance_table.scan(
        ProjectionExpression="eventSeriesId,eventId,endDate,#l,locationType,postcode,startDate,#u",
        ExpressionAttributeNames={
          "#l": "location",
          "#u": "url"
        }
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results
