import boto3
import datetime
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_ALLOCATIONS_INDEX = os.getenv('EVENT_ALLOCATIONS_INDEX')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"EVENT_ALLOCATIONS_INDEX = {EVENT_ALLOCATIONS_INDEX}")
logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

# Caching
event_cache = dict()
series_cache = dict()

def handler(event, context):
  logger.debug(event)

  event_series_id = event['eventSeriesId']
  event_id = event['eventId']
  membership_number = event['membershipNumber']

  logger.debug(f"Getting member details for {membership_number}")
  try:
    member = members_table.get_item(
      Key={
        "membershipNumber": membership_number
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get member {membership_number} from {MEMBERS_TABLE}: {str(e)}")
    raise e
  
  logger.debug(f"Getting event instance details for {event_series_id}/{event_id}")
  event = get_event(event_series_id, event_id)
  
  # TODO: Only query this if required
  logger.debug(f"Getting allocations for {membership_number}")
  try:
    allocations = event_allocations_table.query(
      IndexName=EVENT_ALLOCATIONS_INDEX,
      KeyConditionExpression="membershipNumber=:membershipNumber",
      ExpressionAttributeValues={
        ":membershipNumber": membership_number
      }
    )['Items']
  except Exception as e:
    logger.error(f"Unable to get allocations for {membership_number} from {EVENT_INSTANCE_TABLE}: {str(e)}")
    raise e

  event_start = datetime.date.fromisoformat(event.get("startDate")[0:10])

  allocation_weighting = event.get("weightingCriteria", {})
  if type(allocation_weighting) is not dict:
    allocation_weighting = {}

  rules = allocation_weighting.keys()

  # Calculate weightings
  weightings = {}


  if "under_25" in rules or "over_25" in rules:
    birthday = datetime.date.fromisoformat(member.get("dateOfBirth"))
    event_25_cutoff = datetime.date(event_start.year - 25, event_start.month, event_start.day)

    weightings["under_25"] = 1 if birthday >= event_25_cutoff else 0
    weightings["over_25"] = 1 if birthday < event_25_cutoff else 0

  if "attended" in rules or "attended_1yr" in rules or "attended_2yr" in rules or "attended_3yr" in rules or "attended_5yr" in rules:
    weightings["attended"] = 0
    weightings["attended_1yr"] = 0
    weightings["attended_2yr"] = 0
    weightings["attended_3yr"] = 0
    weightings["attended_5yr"] = 0

    for a in allocations:
      if a['allocation'] != "ATTENDED":
        continue

      series, eid = a["combinedEventId"].split("/", 1)

      if series != event_series_id:
        continue

      ## Has attended event series previously
      weightings["attended"] += 1

      try:
        e = get_event(series, eid)
      except:
        continue

      e_start = datetime.date.fromisoformat(e.get("startDate")[0:10])
      diff = (event_start - e_start)/365.25

      ## Has attended event series in past year
      if diff < 1:
        weightings["attended_1yr"] += 1
      
      ## Has attended event series in past 2 years
      if diff < 2:
        weightings["attended_2yr"] += 1
      
      ## Has attended event series in past 3 years
      if diff < 3:
        weightings["attended_3yr"] += 1
      
      ## Has attended event series in past 5 years
      if diff < 5:
        weightings["attended_5yr"] += 1

  if "droppedout_6mo" in rules or "droppedout_1yr" in rules or "droppedout_2yr" in rules or "droppedout_3yr" in rules:
    weightings["droppedout_6mo"] = 0
    weightings["droppedout_1yr"] = 0
    weightings["droppedout_2yr"] = 0
    weightings["droppedout_3yr"] = 0

    for a in allocations:
      if a['allocation'] != "DROPPED_OUT":
        continue

      series, eid = a["combinedEventId"].split("/", 1)

      try:
        s = get_series(series)
      except:
        continue

      if s.get("type") == "social" or s.get("type") == "no_impact":
        continue

      try:
        e = get_event(series, eid)
      except:
        continue

      e_start = datetime.date.fromisoformat(e.get("startDate")[0:10])
      diff = (event_start - e_start)/365.25

      ## Dropped out in past 6 months
      if diff < 0.5:
        weightings["droppedout_6mo"] += 1
      
      ## Dropped out in past year
      if diff < 1:
        weightings["droppedout_1yr"] += 1
      
      ## Dropped out in past 2 years
      if diff < 2:
        weightings["droppedout_2yr"] += 1
      
      ## Dropped out in past 3 years
      if diff < 3:
        weightings["droppedout_3yr"] += 1

  if "noshow_6mo" in rules or "noshow_1yr" in rules or "noshow_2yr" in rules or "noshow_3yr" in rules:
    weightings["noshow_6mo"] = 0
    weightings["noshow_1yr"] = 0
    weightings["noshow_2yr"] = 0
    weightings["noshow_3yr"] = 0

    for a in allocations:
      if a['allocation'] != "NO_SHOW":
        continue

      series, eid = a["combinedEventId"].split("/", 1)

      try:
        s = get_series(series)
      except:
        continue

      if s.get("type") == "social" or s.get("type") == "no_impact":
        continue

      try:
        e = get_event(series, eid)
      except:
        continue

      e_start = datetime.date.fromisoformat(e.get("startDate")[0:10])
      diff = (event_start - e_start)/365.25

      ## No show in past 6 months
      if diff < 0.5:
        weightings["noshow_6mo"] += 1
      
      ## No show in past year
      if diff < 1:
        weightings["noshow_1yr"] += 1
      
      ## No show in past 2 years
      if diff < 2:
        weightings["noshow_2yr"] += 1
      
      ## No show in past 3 years
      if diff < 3:
        weightings["noshow_3yr"] += 1

  # Check join date
  if "joined_1yr" in rules or "joined_2yr" in rules or "joined_3yr" in rules or "joined_5yr" in rules:
    join_date = datetime.date.fromisoformat(member.get("joinDate"))
    join_date_delta_days = (event_start - join_date).days

    weightings["joined_1yr"] = 1 if join_date_delta_days <= 365 else 0
    weightings["joined_2yr"] = 1 if join_date_delta_days <= 365*2 else 0
    weightings["joined_3yr"] = 1 if join_date_delta_days <= 365*3 else 0
    weightings["joined_5yr"] = 1 if join_date_delta_days <= 365*5 else 0

  if "qsa_1yr" in rules or "qsa_2yr" in rules or "qsa_3yr" in rules or "qsa_5yr" in rules:
    ## TODO: Got QSA within past year
    ## TODO: Got QSA within past 2 years
    ## TODO: Got QSA within past 3 years
    ## TODO: Got QSA within past 5 years
    pass

  return {
    'eventSeriesId': event_series_id,
    'eventId': event_id,
    'membershipNumber': membership_number,
    'weightings': weightings
  }

# TODO: Reduce the amount of data retrieved/cached

def get_series(event_series_id):
  if event_series_id in series_cache:
    return series_cache[event_series_id]
  
  try:
    series = event_series_table.get_item(
      Key={
        "eventSeriesId": event_series_id
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event series {event_series_id} from {EVENT_SERIES_TABLE}: {str(e)}")
    raise e
  
  series_cache[event_series_id] = series
  return series


def get_event(event_series_id, event_id):
  combined_id = f"{event_series_id}/{event_id}"

  if combined_id in event_cache:
    return event_cache[combined_id]

  try:
    event = event_instance_table.get_item(
      Key={
        "eventSeriesId": event_series_id,
        "eventId": event_id
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event instance {event_series_id}/{event_id} from {EVENT_INSTANCE_TABLE}: {str(e)}")
    raise e
  
  event_cache[combined_id] = event
  return event