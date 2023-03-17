import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ALLOCATION_TEMPLATE = os.getenv('EVENT_ALLOCATION_TEMPLATE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
EVENTS_EMAIL = os.getenv('EVENTS_EMAIL')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"EVENT_ALLOCATION_TEMPLATE = {EVENT_ALLOCATION_TEMPLATE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")
logger.info(f"EVENTS_EMAIL = {EVENTS_EMAIL}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):
  logger.debug(event)

  for record in event['Records']:
    if record['eventSource'] != "aws:dynamodb":
      logger.warning(f"Non-DynamoDB event found - skipping: {json.dumps(record)}")
      continue

    if record['eventName'] == "REMOVE":
      logger.info("REMOVE event received - skipping")
      continue

    combinedEventId = record['dynamodb']['Keys']['combinedEventId']['S']
    membershipNumber = record['dynamodb']['Keys']['membershipNumber']['S']

    if 'NewImage' not in record['dynamodb']:
      logger.warning(f"New image not included in record - skipping: {json.dumps(record)}")
      continue

    allocation = record['dynamodb']['NewImage']['allocation']['S']

    logger.info(f"{record['eventName']} event for member {membershipNumber} on {combinedEventId}")

    if record['eventName'] == "INSERT" or record['eventName'] == "MODIFY":
      updated_allocation(combinedEventId, membershipNumber, allocation)


def updated_allocation(combinedEventId, membershipNumber, allocation):
  logger.debug("Sending new/updated allocation notification")

  if allocation == "ALLOCATED":
    a = "Allocated"
    aText = "You have been selected to attend the above event, and will receive further details in due course."
  elif allocation == "RESERVE":
    a = "Reserve list"
    aText = "You have been placed on the reserve list to attend the above event. Please keep the date free if possible."
  elif allocation == "NOT_ALLOCATED":
    a = "Not allocated"
    aText = "You have not been selected to attend the above event. Thank you for offering your time."
  elif allocation == "DROPPED_OUT":
    a = "Dropped out"
    aText = "You have notified us that you will no longer be able to attend this event."
  elif allocation == "NO_SHOW":
    a = "No show"
    aText = "You were due to attend this event, but did not attend without giving us prior notice (or without giving us sufficient notice)."
  else:
    logger.info(f"New allocation status is {allocation} - e-mail will not be sent")
    return

  # Get series details
  eventSeriesId = combinedEventId.split("/", 1)[0]
  try:
    eventSeries = event_series_table.get_item(
      Key={
        "eventSeriesId": eventSeriesId
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event series {eventSeriesId} from {EVENT_SERIES_TABLE}: {str(e)}")
    raise e
  
  # Get member details
  try:
    member = members_table.get_item(
      Key={
        "membershipNumber": membershipNumber
      },
      ProjectionExpression="firstName,preferredName,surname,email"
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get member {membershipNumber} from {MEMBERS_TABLE}: {str(e)}")
    raise e
  
  if member.get('preferredName'):
    firstName = member['preferredName']
    name = f"{member['preferredName']} {member['surname']}"
  else:
    firstName = member['firstName']
    name = f"{member['firstName']} {member['surname']}"

  try:
    ses.send_templated_email(
      Source='"KSWP Portal" <portal@kswp.org.uk>',
      Destination={
        'ToAddresses': [
          '"'+name+'" <'+member['email']+'>',
        ]
      },
      ReplyToAddresses=[
        EVENTS_EMAIL
      ],
      ReturnPath='bounces@kswp.org.uk',
      Template=EVENT_ALLOCATION_TEMPLATE,
      TemplateData=json.dumps({
        'firstName': firstName,
        'eventName': eventSeries['name'],
        'allocation': a,
        'allocationText': aText
      })
    )
  except Exception as e:
    logger.error(f"Unable to send {EVENT_ALLOCATION_TEMPLATE} e-mail to {member['email']} for {membershipNumber} on {combinedEventId}: {str(e)}")
    raise e

  logger.info(f"Finished sending allocation notification for {membershipNumber} on {combinedEventId}")
