
import boto3
from boto3.dynamodb.conditions import Key, Attr
from collections import Counter
import datetime
import json
import logging
import os
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_INDEX = os.getenv('EVENT_ALLOCATIONS_INDEX')
EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_SERIES_TABLE =  os.getenv('EVENT_SERIES_TABLE')
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
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

event_dates = {}
event_types = {}

def handler(event, context):
  # Get ACTIVE members
  try:
    active_members = scan_active_members()
  except Exception as e:
    logger.error(f"Unable to list ACTIVE members: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to list ACTIVE members"
    }

  allocationCount = {
    "REGISTERED": {},
    "ALLOCATED": {},
    "ATTENDED": {},
    "NOT_ALLOCATED": {},
    "RESERVE": {},
    "DROPPED_OUT": {},
    "NO_SHOW": {}
  }

  dayCount = {}

  today = datetime.date.today()
  todayIso = today.isoformat()
  ymd1Yr = f"{today.year - 1}-{today.month:02d}-{today.day:02d}"

  # For each ACTIVE member, count the number of events they've attended in the past year, and the number of days on which they have supported events
  for member in active_members:
    membershipNumber = member["membershipNumber"]

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
    
    count = {
      "REGISTERED": 0,
      "ALLOCATED": 0,
      "ATTENDED": 0,
      "NOT_ALLOCATED": 0,
      "RESERVE": 0,
      "DROPPED_OUT": 0,
      "NO_SHOW": 0
    }

    days = 0

    for allocation in allocations:
      event_type = get_event_type(allocation["combinedEventId"])
      if event_type != "event":
        continue

      start_date, end_date = get_event_dates(allocation["combinedEventId"])
      if start_date is None or end_date is None or start_date < ymd1Yr or start_date > todayIso:
        continue

      if allocation["allocation"] == "ATTENDED":
        sd = datetime.date.fromisoformat(start_date[:10])
        ed = datetime.date.fromisoformat(end_date[:10])
        num_days = abs(ed - sd).days + 1
        days += num_days

      count[allocation["allocation"]] = count.get(allocation["allocation"], 0) + 1
    
    for k, v in count.items():
      if k not in allocationCount:
        continue
      
      allocationCount[k][v] = allocationCount[k].get(v, 0) + 1
    
    dayCount[days] = dayCount.get(days, 0) + 1

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({
      "counts": allocationCount,
      "days": dayCount
    })
  }

def scan_active_members(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = members_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="membershipNumber,#s",
        ExpressionAttributeNames={
          "#s": "status"
        },
        FilterExpression=Attr("status").eq("ACTIVE"),
        **kwargs
      )
    else: 
      response = members_table.scan(
        ProjectionExpression="membershipNumber,#s",
        ExpressionAttributeNames={
          "#s": "status"
        },
        FilterExpression=Attr("status").eq("ACTIVE"),
        **kwargs
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results


def get_event_dates(combined_event_id):
  if combined_event_id in event_dates:
    return event_dates[combined_event_id]

  event_series_id, event_id = combined_event_id.split("/", 1)

  try:
    instance = event_instance_table.get_item(
      Key={
        "eventSeriesId": event_series_id,
        "eventId": event_id
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event instance (Event Series = {event_series_id}, Event ID = {event_id}) from {EVENT_INSTANCE_TABLE}: {str(e)}")
    return (None, None)
    #raise e
  
  event_dates[combined_event_id] = (instance["startDate"], instance["endDate"])

  return (instance["startDate"], instance["endDate"])

def get_event_type(combined_event_id):
  event_series_id, _ = combined_event_id.split("/", 1)

  if event_series_id in event_types:
    return event_types[event_series_id]

  try:
    instance = event_series_table.get_item(
      Key={
        "eventSeriesId": event_series_id,
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event series (Event Series = {event_series_id}) from {EVENT_SERIES_TABLE}: {str(e)}")
    return "unknown"
    #raise e
  
  event_types[event_series_id] = instance["type"]

  return instance["type"]
