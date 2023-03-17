import json
import boto3
from   boto3.dynamodb.conditions import Attr
import datetime
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

ALLOCATION_REMINDER_TEMPLATE = os.getenv('ALLOCATION_REMINDER_TEMPLATE')
EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
EVENTS_EMAIL = os.getenv('EVENTS_EMAIL')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')

logger.info(f"ALLOCATION_REMINDER_TEMPLATE = {ALLOCATION_REMINDER_TEMPLATE}")
logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")
logger.info(f"EVENTS_EMAIL = {EVENTS_EMAIL}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)

def handler(event, context):
  yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
  logger.info(f"Yesterday's date: {yesterday}")

  # Find all events that finished yesterday
  try:
    finished_events = event_instance_table.scan(
      FilterExpression=Attr('endDate').begins_with(yesterday)
    )['Items']
  except Exception as ex:
    logger.error(f"Unable to scan for events that finished yesterday: {str(ex)}")
    raise ex

  logger.info(f"{len(finished_events)} events found that finished yesterday")
  
  # Find all events that registration closed yesterday
  try:
    closed_events = event_instance_table.scan(
      FilterExpression=Attr('registrationDate').eq(yesterday)
    )['Items']
  except Exception as ex:
    logger.error(f"Unable to scan for events that closed yesterday: {str(ex)}")
    raise ex

  logger.info(f"{len(closed_events)} events found that closed yesterday")

  # Get event names - TODO: Avoid looking up the same key multiple times
  closed = []
  for event in closed_events:
    try:
      series = event_series_table.get_item(
        Key={
          'eventSeriesId': event["eventSeriesId"]
        }
      )['Item']

      closed.append({
        "eventSeriesId": event["eventSeriesId"],
        "eventId": event["eventId"],
        "location": event["location"],
        "name": series["name"]
      })
    except Exception as ex:
      logger.error(f"Unable to get event series information for {event['eventSeriesId']}: {str(ex)}")
      continue

  finished = []
  for event in finished_events:
    try:
      series = event_series_table.get_item(
        Key={
          'eventSeriesId': event["eventSeriesId"]
        }
      )['Item']

      finished.append({
        "eventSeriesId": event["eventSeriesId"],
        "eventId": event["eventId"],
        "location": event["location"],
        "name": series["name"]
      })
    except Exception as ex:
      logger.error(f"Unable to get event series information for {event['eventSeriesId']}: {str(ex)}")
      continue

  # Send e-mail
  if len(finished) + len(closed) > 0:
    logger.info("Sending allocation reminder e-mail")

    try:
      response = ses.send_templated_email(
        Source='"KSWP Portal" <portal@kswp.org.uk>',
        Destination={
          'ToAddresses': [
            EVENTS_EMAIL
          ]
        },
        ReturnPath='bounces@kswp.org.uk',
        Template=ALLOCATION_REMINDER_TEMPLATE,
        TemplateData=json.dumps({
          'portalDomain': PORTAL_DOMAIN,
          'finished': finished if len(finished) else None,
          'closed': closed if len(closed) else None
        })
      )

      logger.info(f"Message sent with ID {response.get('MessageId', 'unknown')}")

    except Exception as ex:
      logger.error(f"Unable to send {ALLOCATION_REMINDER_TEMPLATE} e-mail to {EVENTS_EMAIL}: {str(ex)}")
      raise ex