import json
import boto3
from   boto3.dynamodb.conditions import Attr
import datetime
from dateutil.relativedelta import relativedelta
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_INSTANCE_TABLE = os.getenv('EVENT_INSTANCE_TABLE')
EVENT_REMINDER_TEMPLATE = os.getenv('EVENT_REMINDER_TEMPLATE')
EVENT_SERIES_TABLE = os.getenv('EVENT_SERIES_TABLE')
EVENTS_EMAIL = os.getenv('EVENTS_EMAIL')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')

logger.info(f"EVENT_INSTANCE_TABLE = {EVENT_INSTANCE_TABLE}")
logger.info(f"EVENT_REMINDER_TEMPLATE = {EVENT_REMINDER_TEMPLATE}")
logger.info(f"EVENT_SERIES_TABLE = {EVENT_SERIES_TABLE}")
logger.info(f"EVENTS_EMAIL = {EVENTS_EMAIL}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")

MONTHS = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE)
event_series_table = dynamodb.Table(EVENT_SERIES_TABLE)

def handler(event, context):
  # Find all events that started 8 months ago
  year_month = (datetime.date.today() + relativedelta(months=-8)).isoformat()[0:7]
  year = int(year_month[0:4])
  month = int(year_month[5:])
  logger.info(f"8 months ago: {year_month}")

  # Find all events that finished yesterday
  try:
    events = event_instance_table.scan(
      FilterExpression=Attr('startDate').begins_with(year_month)
    )['Items']
  except Exception as ex:
    logger.error(f"Unable to scan for events that started 8 months ago: {str(ex)}")
    raise ex

  logger.info(f"{len(events)} events found that started 8 months ago")

  # Get event names - TODO: Avoid looking up the same key multiple times
  event_details = []
  for event in events:
    try:
      series = event_series_table.get_item(
        Key={
          'eventSeriesId': event["eventSeriesId"]
        }
      )['Item']

      event_details.append({
        "eventSeriesId": event["eventSeriesId"],
        "eventId": event["eventId"],
        "location": event["location"],
        "name": series["name"]
      })
    except Exception as ex:
      logger.error(f"Unable to get event series information for {event['eventSeriesId']}: {str(ex)}")
      continue

  # Send e-mail
  if len(event_details) > 0:
    logger.info("Sending event reminder e-mail")

    try:
      response = ses.send_templated_email(
        Source='"QSWP Portal" <portal@qswp.org.uk>',
        Destination={
          'ToAddresses': [
            EVENTS_EMAIL
          ]
        },
        ReturnPath='bounces@qswp.org.uk',
        Template=EVENT_REMINDER_TEMPLATE,
        TemplateData=json.dumps({
          'portalDomain': PORTAL_DOMAIN,
          'eventDetails': event_details,
          'month': MONTHS[month],
          'year': year
        })
      )

      logger.info(f"Message sent with ID {response.get('MessageId', 'unknown')}")

    except Exception as ex:
      logger.error(f"Unable to send {EVENT_REMINDER_TEMPLATE} e-mail to {EVENTS_EMAIL}: {str(ex)}")
      raise ex