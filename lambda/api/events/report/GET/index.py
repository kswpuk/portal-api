
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

  # TODO: Count of drop outs, no shows, attendees, reserve list
  # TODO: People who haven't attended at least two events in the last 12 months

  # Get event instances
  try:
    instances = scan_event_instances()
  except Exception as e:
    logger.error(f"Unable to get event instances: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get event instances"
    }

  # Get event series
  try:
    series = scan_event_series()
  except Exception as e:
    logger.error(f"Unable to get event series: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get event series"
    }
  
  instances_event = [i for i in instances if series[i['eventSeriesId']] == 'event']
  instances_socials = [i for i in instances if series[i['eventSeriesId']] == 'social']

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({
      "events": generate_event_stats(instances_event, get_allocations=True),
      "socials": generate_event_stats(instances_socials)
    })
  }

def generate_event_stats(instances, get_allocations=False):
  today = datetime.date.today()

  ym1Yr = f"{today.year - 1}-{today.month:02d}"
  ymd1Yr = f"{today.year - 1}-{today.month:02d}-{today.day:02d}"
  y5Yr = f"{today.year - 5}-01"

  startDates = [instance['startDate'][0:7] for instance in instances if instance['startDate'][0:7] >= y5Yr]
  startDatesCount = Counter(startDates)

  eventsPastYear = 0
  hoursPastYear = 0.0
  oversubscribedPastYear = 0
  postcodesPastYear = []
  eventsUpcoming = 0
  nextEvent = None

  for i in instances:
    if i['startDate'] >= ymd1Yr and i['startDate'] <= today.isoformat():
      eventsPastYear += 1
      postcodesPastYear.append(get_area(i['postcode']))

      if get_allocations:
        allocations = get_event_allocations(i['eventSeriesId'], i['eventId'])
      else:
        allocations = []
      
      # Calculate the number of volunteer hours for this event
      attended = len([a for a in allocations if a["allocation"] == "ATTENDED"])
      start = datetime.datetime.fromisoformat(i['startDate'])
      end = datetime.datetime.fromisoformat(i['endDate'])
      eventLength = end - start

      hours = (eventLength.days * 24) + (eventLength.seconds / 86400)
      hoursPastYear += hours*attended

      # Oversubscribed if total allocations are greater than the number of places
      attendanceLimit = int(i.get('attendanceLimit', 0))
      if attendanceLimit > 0 and len(allocations) > attendanceLimit:
        oversubscribedPastYear += 1

    elif i['startDate'] > today.isoformat():
      eventsUpcoming += 1
      if nextEvent is None or nextEvent > i['startDate']:
        nextEvent = i['startDate'][0:10]

  if nextEvent is not None:
    d = datetime.date.fromisoformat(nextEvent)

    nextEventDate = d.isoformat()
    nextEventDays = (d - today).days
  else:
    nextEventDate = None
    nextEventDays = None

  return {
    "counts": {
      "startDates": startDatesCount,
      "pastYear": eventsPastYear,
      "pastYearHours": round(hoursPastYear),
      "pastYearOversubscribed": oversubscribedPastYear,
      "postcodesPastYear": Counter(postcodesPastYear),
      "upcoming": eventsUpcoming
    },
    "next": nextEventDate,
    "nextDays": nextEventDays
  }

def get_area(postcode):
  return re.split(r'[\d\s]', postcode)[0]

def scan_event_instances(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = event_instance_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="eventSeriesId,eventId,startDate,endDate,attendanceLimit,postcode",
        **kwargs
      )
    else: 
      response = event_instance_table.scan(
        ProjectionExpression="eventSeriesId,eventId,startDate,endDate,attendanceLimit,postcode",
        **kwargs
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results

def scan_event_series(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = event_series_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="eventSeriesId,#t",
        ExpressionAttributeNames={
          "#t": "type"
        },
        **kwargs
      )
    else: 
      response = event_series_table.scan(
        ProjectionExpression="eventSeriesId,#t",
        ExpressionAttributeNames={
          "#t": "type"
        },
        **kwargs
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return { e['eventSeriesId'] : e['type'] for e in results }

def get_event_allocations(event_series_id, event_id):
  combined_event_id = event_series_id + "/" + event_id
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