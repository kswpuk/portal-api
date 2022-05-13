import boto3
from   boto3.dynamodb.conditions import Key
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

APPLICATION_TABLE = os.getenv('APPLICATION_TABLE')
MEMBERS_EMAIL = os.getenv('MEMBERS_EMAIL')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')
REFERENCE_REQUEST_TEMPLATE = os.getenv('REFERENCE_REQUEST_TEMPLATE')
REFERENCE_RECEIVED_TEMPLATE = os.getenv('REFERENCE_RECEIVED_TEMPLATE')

logger.info(f"APPLICATION_TABLE = {APPLICATION_TABLE}")
logger.info(f"MEMBERS_EMAIL = {MEMBERS_EMAIL}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")
logger.info(f"REFERENCE_REQUEST_TEMPLATE = {REFERENCE_REQUEST_TEMPLATE}")
logger.info(f"REFERENCE_RECEIVED_TEMPLATE = {REFERENCE_RECEIVED_TEMPLATE}")

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

table = dynamodb.Table(APPLICATION_TABLE)


def handler(event, context):
  logger.debug(event)

  for record in event['Records']:
    if record['eventSource'] != "aws:dynamodb":
      logger.warning(f"Non-DynamoDB event found - skipping: {json.dumps(record)}")
      continue

    membershipNumber = record['dynamodb']['Keys']['membershipNumber']['S']
    logger.info(f"{record['eventName']} event for {membershipNumber}")

    if record['eventName'] == "INSERT" or record['eventName'] == "MODIFY":
      r = record['dynamodb']['NewImage']
      
      logger.debug("Getting applicant information")
      try:
        applications = table.get_item(
          Key={
            "membershipNumber":  membershipNumber
          },
          ProjectionExpression="membershipNumber,firstName,surname,email"
        )
      except Exception as e:
        logger.error(f"Unable to get applicant information for {r['membershipNumber']}: {str(e)}")
        raise e
      
      if 'Item' not in applications or applications['Item'] is None:
        logger.warning(f"No application found for {r['membershipNumber']} - reference invitation will not be sent")
        return

      a = applications['Item']
      
      if 'submittedAt' in r and r['submittedAt']:
        reference_completed(r, a)
      else:
        referee_added(r, a)


def reference_completed(reference, application):
  logger.debug("Sending completed reference")

  name = application['firstName'] + " " + application['surname']
  referenceName = reference['referenceName']['S']
  referenceEmail = reference['referenceEmail']['S']
  try:
    ses.send_templated_email(
      Source='"QSWP Portal" <portal@qswp.org.uk>',
      Destination={
        'ToAddresses': [
          '"'+referenceName+'" <'+referenceEmail+'>',
        ],
        'CcAddresses': [
          MEMBERS_EMAIL
        ]
      },
      ReplyToAddresses=[
        MEMBERS_EMAIL
      ],
      ReturnPath='bounces@qswp.org.uk',
      Template=REFERENCE_RECEIVED_TEMPLATE,
      TemplateData=json.dumps({
        'referenceName': referenceName,
        'name': name
      })
    )
  except Exception as e:
    logger.error(f"Unable to send {REFERENCE_RECEIVED_TEMPLATE} e-mail to {referenceEmail} for {application['membershipNumber']}: {str(e)}")
    raise e
  
  logger.info(f"{REFERENCE_RECEIVED_TEMPLATE} e-mail sent to {referenceEmail} for {application['membershipNumber']}")


def referee_added(reference, application):
  logger.debug("Sending reference invitation")

  name = application['firstName'] + " " + application['surname']
  referenceName = reference['referenceName']['S']
  referenceEmail = reference['referenceEmail']['S']
  try:
    ses.send_templated_email(
      Source='"QSWP Portal" <portal@qswp.org.uk>',
      Destination={
        'ToAddresses': [
          '"'+referenceName+'" <'+referenceEmail+'>',
        ],
        'CcAddresses': [
          '"'+name+'" <'+application['email']+'>',
        ]
      },
      ReplyToAddresses=[
        MEMBERS_EMAIL
      ],
      ReturnPath='bounces@qswp.org.uk',
      Template=REFERENCE_REQUEST_TEMPLATE,
      TemplateData=json.dumps({
        'referenceName': referenceName,
        'name': name,
        'membershipNumber': application['membershipNumber'],
        'portalDomain': PORTAL_DOMAIN
      })
    )
  except Exception as e:
    logger.error(f"Unable to send {REFERENCE_REQUEST_TEMPLATE} e-mail to {referenceEmail} for {application['membershipNumber']}: {str(e)}")
    raise e
  
  logger.info(f"{REFERENCE_REQUEST_TEMPLATE} e-mail sent to {referenceEmail} for {application['membershipNumber']}")

