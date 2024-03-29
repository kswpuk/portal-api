import boto3
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

event_start_dates = {}
event_types = {}

def handler(event, context):
  """
  Identifies members who should be considered for a good service award, having shown dedication to the KSWP over the last 5 years.
  5 years is the period over which exemplary service must be shown to receive a good service award (https://www.scouts.org.uk/volunteers/learning-development-and-awards/awards-and-recognition/good-service-awards/).

  The criteria used are:
  * Has been a member of the KSWP for at least 5 years
  * Hasn't been a "No Show" at an event they were supposed to attend in the past 5 years
  * Hasn't been a "Drop Out" at more than three events in the past 5 years
  * Has attended events regularly (at least once every 3 months on average) over the past 5 years

  Additionally, although not checked here, members should not have received a good service award within the last 5 years.
  This can be checked on Compass.
  """

  # Get members
  try:
    members = scan_active_members()
  except Exception as e:
    logger.error(f"Unable to list active members: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to list active members"
    }

  to_consider = []

  # Has been a member of the KSWP for at least 5 years
  members_5yrs = [m for m in members if calculate_years(m['joinDate']) >= 5]
  logger.info(f"{len(members_5yrs)} members have been KSWP members for at least 5 years")

  for member in members_5yrs:
    # Get event allocations
    allocations = get_event_allocations(member["membershipNumber"])
    event_allocations = [a for a in allocations if get_event_type(a["combinedEventId"]) == "event"]

    # Hasn't been a "No Show" at an event they were supposed to attend in the past 5 years
    no_show = [a for a in event_allocations if a["allocation"] == "NO_SHOW"]

    if len(no_show) > 0:
      logger.info(f'Rejecting {member["membershipNumber"]} as they have been a no show at {len(no_show)} event(s) over the past 5 years')
      continue

    # Hasn't been a "Drop Out" at more than three events in the past 5 years
    drop_out = [a for a in event_allocations if a["allocation"] == "DROP_OUT"]

    if len(drop_out) > 3:
      logger.info(f'Rejecting {member["membershipNumber"]} as they have been a drop out at {len(no_show)} event(s) over the past 5 years')
      continue

    # Has attended events regularly (at least once every 3 months on average) over the past 5 years
    attended = [a for a in event_allocations if a["allocation"] == "ATTENDED"]

    if len(attended) < 20:
      logger.info(f'Rejecting {member["membershipNumber"]} as they have only attended {len(no_show)} event(s) over the past 5 years')
      continue


    logger.info(f'Adding {member["membershipNumber"]} to the list of members to consider')
    to_consider.append(member)

  logger.info(f'{len(to_consider)} members should be considered for awards')

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({
      "members": [
        {
          "membershipNumber": m["membershipNumber"],
          "firstName": m["firstName"],
          "surname": m["surname"]
        } for m in to_consider
      ]
    })
  }

def scan_active_members(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = members_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="membershipNumber,firstName,surname,joinDate,#s",
        ExpressionAttributeNames={
          "#s": "status"
        },
        FilterExpression="#s=:s",
        ExpressionAttributeValues={
          ":s": "ACTIVE"
        },
        **kwargs
      )
    else: 
      response = members_table.scan(
        ProjectionExpression="membershipNumber,firstName,surname,joinDate,#s",
        ExpressionAttributeNames={
          "#s": "status"
        },
        FilterExpression="#s=:s",
        ExpressionAttributeValues={
          ":s": "ACTIVE"
        },
        **kwargs
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results


def get_event_allocations(membership_number, years = 5):
  try:
    allocations = event_allocations_table.query(
      IndexName=EVENT_ALLOCATIONS_INDEX,
      KeyConditionExpression="membershipNumber=:membershipNumber",
      ExpressionAttributeValues={
        ":membershipNumber": membership_number
      }
    )['Items']
  except Exception as e:
    logger.error(f"Unable to get allocations for member {membership_number}: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Couldn't get allocations"
    }
  
  return [a for a in allocations if calculate_years(get_start_date(a["combinedEventId"])) < years]


def get_start_date(combined_event_id):
  if combined_event_id in event_start_dates:
    return event_start_dates[combined_event_id]

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
    raise e

  event_start_dates[combined_event_id] = instance["startDate"]

  return instance["startDate"]


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
    raise e
  
  event_types[event_series_id] = instance["type"]

  return instance["type"]


def calculate_years(d):
  today = datetime.date.today()
  then = datetime.date.fromisoformat(d[0:10])

  return today.year - then.year - ((today.month, today.day) < (then.month, then.day))