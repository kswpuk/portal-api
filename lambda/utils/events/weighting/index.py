import boto3
import datetime
import logging
import os

# Default allocation weighting
DEFAULT_ALLOCATION_WEIGHTING = {
  "under_25": 1,
  "joined_1yr": 1
}

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATIONS_TABLE = os.getenv('EVENT_ALLOCATIONS_TABLE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"EVENT_ALLOCATIONS_TABLE = {EVENT_ALLOCATIONS_TABLE}")
logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_allocations_table = dynamodb.Table(EVENT_ALLOCATIONS_TABLE)
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

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

  event_start = datetime.date.fromisoformat(event.get("startDate")[0:10])

  allocation_weighting = event.get("allocationWeighting", DEFAULT_ALLOCATION_WEIGHTING)
  if type(allocation_weighting) is not dict or len(allocation_weighting.keys()) == 0:
    allocation_weighting = DEFAULT_ALLOCATION_WEIGHTING

  rules = allocation_weighting.keys()

  # Calculate weightings
  weightings = {}


  if "under_25" in rules or "over_25" in rules:
    birthday = datetime.date.fromisoformat(member.get("dateOfBirth"))
    event_25_cutoff = datetime.date(event_start.year - 25, event_start.month, event_start.day)

    weightings["under_25"] = 1 if birthday >= event_25_cutoff else 0
    weightings["over_25"] = 1 if birthday < event_25_cutoff else 0

  if "attended" in rules or "attended_1yr" in rules or "attended_2yr" in rules or "attended_3yr" in rules or "attended_5yr" in rules:
    ## TODO: Has attended event series previously
    ## TODO: Has attended event series in past year
    ## TODO: Has attended event series in past 2 years
    ## TODO: Has attended event series in past 3 years
    ## TODO: Has attended event series in past 5 years
    pass

  ## TODO: Make sure we exclude social/no_impact events

  if "droppedout_6mo" in rules or "droppedout_1yr" in rules or "droppedout_2yr" in rules or "droppedout_3yr" in rules:
    ## TODO: Dropped out in past 6 months
    ## TODO: Dropped out in past year
    ## TODO: Dropped out in past 2 years
    ## TODO: Dropped out in past 3 years
    pass

  if "noshow_6mo" in rules or "noshow_1yr" in rules or "noshow_2yr" in rules or "noshow_3yr" in rules:
    ## TODO: No show in past 6 months
    ## TODO: No show in past year
    ## TODO: No show in past 2 years
    ## TODO: No show in past 3 years
    pass

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