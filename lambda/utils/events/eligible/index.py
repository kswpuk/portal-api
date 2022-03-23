
from cmath import exp
import boto3
import datetime
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):
  event_series_id = event['eventSeriesId']
  event_id = event['eventId']
  membership_number = event['membershipNumber']
  
  try:
    member = members_table.get_item(
      Key={
        "membershipNumber": membership_number
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get member {membership_number} from {MEMBERS_TABLE}: {str(e)}")
    raise e

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
  
  rules = []
  
  for r in instance.get("attendanceCriteria", []):
    if r == "active":
      rules.append(wrangle(r, evaluate_active(member)))
    elif r == "under25":
      rules.append(wrangle(r, evaluate_under25(member, instance)))
    elif r == "over25":
      rules.append(wrangle(r, evaluate_over25(member, instance)))
    else:
      logger.warn(f"Unexpected rule {r} - rule will be ignored")

  return {
    "eligible": not any(r["passed"] is False for r in rules),
    "rules": rules
  }

def wrangle(rule_id, result):
  return {
    "id": rule_id,
    "passed": result
  }

def evaluate_active(member):
  expires = datetime.date.fromisoformat(member.get("membershipExpires", "1970-01-01"))
  today = datetime.date.today()

  return expires >= today

def evaluate_under25(member, event):
  birthday = datetime.date.fromisoformat(member.get("dateOfBirth"))

  event = datetime.date.fromisoformat(event.get("startDate")[0:10])
  cutoff = datetime.date(event.year - 25, event.month, event.day)

  return birthday >= cutoff

def evaluate_over25(member, event):
  birthday = datetime.date.fromisoformat(member.get("dateOfBirth"))

  event = datetime.date.fromisoformat(event.get("startDate")[0:10])
  cutoff = datetime.date(event.year - 25, event.month, event.day)

  return birthday < cutoff