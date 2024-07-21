import boto3
from   boto3.dynamodb.conditions import Attr,Key
import datetime
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

ALLOCATIONS_TABLE = os.getenv('ALLOCATIONS_TABLE')
EVENT_ADDED_TEMPLATE = os.getenv('EVENT_ADDED_TEMPLATE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
EVENTS_EMAIL = os.getenv('EVENTS_EMAIL')
MEMBERS_STATUS_INDEX = os.getenv('MEMBERS_STATUS_INDEX')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')

logger.info(f"ALLOCATIONS_TABLE = {ALLOCATIONS_TABLE}")
logger.info(f"EVENT_ADDED_TEMPLATE = {EVENT_ADDED_TEMPLATE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")
logger.info(f"EVENTS_EMAIL = {EVENTS_EMAIL}")

logger.info(f"MEMBERS_STATUS_INDEX = {MEMBERS_STATUS_INDEX}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

allocations_table = dynamodb.Table(ALLOCATIONS_TABLE)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):
  logger.debug(event)

  for record in event['Records']:
    if record['eventSource'] != "aws:dynamodb":
      logger.warning(f"Non-DynamoDB event found - skipping: {json.dumps(record)}")
      continue

    eventSeriesId = record['dynamodb']['Keys']['eventSeriesId']['S']
    eventId = record['dynamodb']['Keys']['eventId']['S']
    logger.info(f"{record['eventName']} event for {eventSeriesId}/{eventId}")

    if record['eventName'] == "INSERT":
      e = record['dynamodb']['NewImage']
      new_event(eventSeriesId, e)
    elif record['eventName'] == "REMOVE":
      remove_event(eventSeriesId, eventId)


def new_event(eventSeriesId, eventInstance):
  logger.debug("Sending new event notification")

  # Get series details
  try:
    eventSeries = event_series_table.get_item(
      Key={
        "eventSeriesId": eventSeriesId
      }
    )['Item']
  except Exception as e:
    logger.error(f"Unable to get event series {eventSeriesId} from {EVENT_SERIES_TABLE}: {str(e)}")
    raise e

  # Get a list of all ACTIVE members
  error_count = 0
  success_count = 0

  for member in get_members(eventInstance['startDate']['S'][0:10], eventInstance['attendanceCriteria']['L']):
    logger.debug(f"Sending event notification to {member['email']}")

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
        Template=EVENT_ADDED_TEMPLATE,
        TemplateData=json.dumps({
          'firstName': firstName,
          'eventSeriesId': eventSeriesId,
          'eventInstanceId': eventInstance['eventId']['S'],
          'eventName': eventSeries['name'],
          'eventDescription': eventSeries['description'],
          'startDate': eventInstance['startDate']['S'],
          'endDate': eventInstance['endDate']['S'],
          'location': eventInstance['location']['S'],
          'registrationDate': eventInstance['registrationDate']['S'],
          'portalDomain': PORTAL_DOMAIN
        })
      )

      success_count += 1
    except Exception as e:
      logger.error(f"Unable to send {EVENT_ADDED_TEMPLATE} e-mail to {member['email']} for {eventSeriesId}/{eventInstance['eventId']}: {str(e)}")
      error_count += 1

  logger.info(f"Finished sending notifications for event {eventSeriesId}/{eventInstance['eventId']} - {success_count} successful, {error_count} errors")


def remove_event(eventSeriesId, eventId):
  combined_event_id = f"{eventSeriesId}/{eventId}"
  allocations = get_allocations(combined_event_id)

  for allocation in allocations:
    try:
      allocations_table.delete_item(
        Key={
          "combinedEventId": combined_event_id,
          "membershipNumber": allocation["membershipNumber"]
        }
      )
    except Exception as e:
      logger.warn(f"Unable to delete allocation of {allocation['membershipNumber']} for {combinedEventId}: {str(e)}")

def get_cutoff(event_date):
  event = datetime.date.fromisoformat(event_date)
  return datetime.date(event.year - 25, event.month, event.day).isoformat()

def get_members(event_date, attendance_criteria):
  results = []
  last_evaluated_key = None

  query_filter = {}
  if "under25" in [x['S'] for x in attendance_criteria]:
    query_filter["FilterExpression"] = Attr('dateOfBirth').gte(get_cutoff(event_date))
  elif "over25" in [x['S'] for x in attendance_criteria]:
    query_filter["FilterExpression"] = Attr('dateOfBirth').lte(get_cutoff(event_date))

  # TODO: Filter by active?

  while True:
    if last_evaluated_key:
      response = members_table.query(
        IndexName=MEMBERS_STATUS_INDEX,
        KeyConditionExpression=Key("status").eq("ACTIVE"),
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="firstName,preferredName,surname,email",
        **query_filter
      )
    else: 
      response = members_table.query(
        IndexName=MEMBERS_STATUS_INDEX,
        KeyConditionExpression=Key("status").eq("ACTIVE"),
        ProjectionExpression="firstName,preferredName,surname,email",
        **query_filter
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results


def get_allocations(combined_event_id):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = allocations_table.query(
        KeyConditionExpression=Key("combinedEventId").eq(combined_event_id),
        ExclusiveStartKey=last_evaluated_key
      )
    else: 
      response = allocations_table.query(
        KeyConditionExpression=Key("combinedEventId").eq(combined_event_id)
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results