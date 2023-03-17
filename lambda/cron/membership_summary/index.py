import json
import boto3
from   boto3.dynamodb.conditions import Key, Attr
import datetime
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

APPLICATIONS_TABLE = os.getenv('APPLICATIONS_TABLE')
MEMBERS_EMAIL = os.getenv('MEMBERS_EMAIL')
MEMBERSHIP_SUMMARY_TEMPLATE = os.getenv('MEMBERSHIP_SUMMARY_TEMPLATE')
MEMBERSHIP_TABLE = os.getenv('MEMBERSHIP_TABLE')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')
REFERENCES_TABLE = os.getenv('REFERENCES_TABLE')
STATUS_INDEX_NAME = os.getenv('STATUS_INDEX_NAME')

logger.info(f"APPLICATIONS_TABLE = {APPLICATIONS_TABLE}")
logger.info(f"MEMBERS_EMAIL = {MEMBERS_EMAIL}")
logger.info(f"MEMBERSHIP_SUMMARY_TEMPLATE = {MEMBERSHIP_SUMMARY_TEMPLATE}")
logger.info(f"MEMBERSHIP_TABLE = {MEMBERSHIP_TABLE}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")
logger.info(f"REFERENCES_TABLE = {REFERENCES_TABLE}")
logger.info(f"STATUS_INDEX_NAME = {STATUS_INDEX_NAME}")

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

applications_table = dynamodb.Table(APPLICATIONS_TABLE)
membership_table = dynamodb.Table(MEMBERSHIP_TABLE)
references_table = dynamodb.Table(REFERENCES_TABLE)

def handler(event, context):
  yesterday = datetime.date.today() - datetime.timedelta(days=1)
  oneWeekAgo = yesterday - datetime.timedelta(days=6)

  renewalsStart = (oneWeekAgo + datetime.timedelta(days=365)).isoformat()
  renewalsEnd = (yesterday + datetime.timedelta(days=365)).isoformat()

  expiredStart = (oneWeekAgo - datetime.timedelta(days=60)).isoformat()
  expiredEnd = (yesterday - datetime.timedelta(days=60)).isoformat()

  applicationsStart = datetime.datetime(oneWeekAgo.year, oneWeekAgo.month, oneWeekAgo.day, 0, 0, 0)
  applicationsEnd = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)

  # Find ACTIVE members who renewed in the last week (expiry date is 1 year in the future)
  try:
    renewals = membership_table.query(
      IndexName=STATUS_INDEX_NAME,
      KeyConditionExpression=Key('status').eq('ACTIVE') & Key('membershipExpires').between(renewalsStart, renewalsEnd),
      ProjectionExpression="membershipNumber,firstName,surname"
    )['Items']
  except Exception as e:
    logger.error(f"Unable to get list of members who renewed last week: {str(e)}")
    renewals = []
  
  logger.info(f"{len(renewals)} members renewed in the past week")

  # Find INACTIVE members who expired two months ago
  try:
    expired = membership_table.query(
      IndexName=STATUS_INDEX_NAME,
      KeyConditionExpression=Key('status').eq('INACTIVE') & Key('membershipExpires').between(expiredStart, expiredEnd),
      ProjectionExpression="membershipNumber,firstName,surname"
    )['Items']
  except Exception as e:
    logger.error(f"Unable to get list of members who expired two months: {str(e)}")
    expired = []
  
  logger.info(f"{len(expired)} members expired two months ago")

  
  # Find applications from the last week
  try:
    applications = applications_table.scan(
      FilterExpression=Attr('submittedAt').between(int(applicationsStart.timestamp()), int(applicationsEnd.timestamp())),
      ProjectionExpression="membershipNumber,firstName,surname"
    )['Items']
  except Exception as e:
    logger.error(f"Unable to get list of applications received last week: {str(e)}")
    applications = []
  
  logger.info(f"{len(applications)} applications received in the past week")

  # Find references from the last week
  try:
    references = references_table.scan(
      FilterExpression=Attr('submittedAt').between(int(applicationsStart.timestamp()), int(applicationsEnd.timestamp())),
      ProjectionExpression="membershipNumber,referenceName"
    )['Items']
  except Exception as e:
    logger.error(f"Unable to get list of references received last week: {str(e)}")
    references = []
  
  logger.info(f"{len(references)} references received in the past week")

  # Send e-mail
  if len(renewals) + len(expired) + len(applications) + len(references) > 0:
    logger.info("Sending membership summary e-mail")

    try:
      response = ses.send_templated_email(
        Source='"KSWP Portal" <portal@kswp.org.uk>',
        Destination={
          'ToAddresses': [
            MEMBERS_EMAIL
          ]
        },
        ReturnPath='bounces@kswp.org.uk',
        Template=MEMBERSHIP_SUMMARY_TEMPLATE,
        TemplateData=json.dumps({
          'portalDomain': PORTAL_DOMAIN,
          'expired': expired if len(expired) else None,
          'expiredStart': expiredStart,
          'expiredEnd': expiredEnd,
          'renewals': renewals if len(renewals) else None,
          'renewalsStart': oneWeekAgo.isoformat(),
          'renewalsEnd': yesterday.isoformat(),
          'applications': applications if len(applications) else None,
          'applicationsStart': oneWeekAgo.isoformat(),
          'applicationsEnd': yesterday.isoformat(),
          'references': references if len(references) else None
        })
      )

      logger.info(f"Message sent with ID {response.get('MessageId', 'unknown')}")

    except Exception as ex:
      logger.error(f"Unable to send {MEMBERSHIP_SUMMARY_TEMPLATE} e-mail to {MEMBERS_EMAIL}: {str(ex)}")
      raise ex