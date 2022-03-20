import boto3
from   boto3.dynamodb.conditions import Key
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_ADDED_TEMPLATE = os.getenv('EVENT_ADDED_TEMPLATE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')

logger.info(f"EVENT_ADDED_TEMPLATE = {EVENT_ADDED_TEMPLATE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")

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

    eventSeriesId = record['dynamodb']['Keys']['eventSeriesId']['S']
    eventId = record['dynamodb']['Keys']['eventId']['S']
    logger.info(f"{record['eventName']} event for {eventSeriesId}/{eventId}")

    if record['eventName'] == "INSERT":
      e = record['dynamodb']['NewImage']
      new_event(eventSeriesId, e)


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

  # Get a list of all members
  error_count = 0
  success_count = 0

  for member in get_members():
    logger.debug(f"Sending event notification to {member['email']}")

    if member.get('preferredName'):
      firstName = member['preferredName']
      name = f"{member['preferredName']} {member['surname']}"
    else:
      firstName = member['firstName']
      name = f"{member['firstName']} {member['surname']}"

    try:
      ses.send_templated_email(
        Source='"QSWP Portal" <portal@qswp.org.uk>',
        Destination={
          'ToAddresses': [
            '"'+name+'" <'+member['email']+'>',
          ]
        },
        ReplyToAddresses=[
            '"QSWP Event Coordinator" <events@qswp.org.uk>',
        ],
        ReturnPath='bounces@qswp.org.uk',
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


def get_members():
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = members_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="firstName,preferredName,surname,email"
      )
    else: 
      response = members_table.scan(
        ProjectionExpression="firstName,preferredName,surname,email"
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results
