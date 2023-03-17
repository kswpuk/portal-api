import boto3
from   boto3.dynamodb.conditions import Key
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

APPLICATION_RECEIVED_TEMPLATE = os.getenv('APPLICATION_RECEIVED_TEMPLATE')
EVIDENCE_BUCKET_NAME = os.getenv('EVIDENCE_BUCKET_NAME')
MEMBERS_EMAIL = os.getenv('MEMBERS_EMAIL')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')
REFERENCES_TABLE = os.getenv('REFERENCES_TABLE')

logger.info(f"APPLICATION_RECEIVED_TEMPLATE = {APPLICATION_RECEIVED_TEMPLATE}")
logger.info(f"EVIDENCE_BUCKET_NAME = {EVIDENCE_BUCKET_NAME}")
logger.info(f"MEMBERS_EMAIL = {MEMBERS_EMAIL}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")
logger.info(f"REFERENCES_TABLE = {REFERENCES_TABLE}")

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
ses = boto3.client('ses')


def handler(event, context):
  logger.debug(event)

  for record in event['Records']:
    if record['eventSource'] != "aws:dynamodb":
      logger.warning(f"Non-DynamoDB event found - skipping: {json.dumps(record)}")
      continue

    membershipNumber = record['dynamodb']['Keys']['membershipNumber']['S']
    logger.info(f"{record['eventName']} event for {membershipNumber}")

    if record['eventName'] == "INSERT":
      a = record['dynamodb']['NewImage']
      application_received(a)
    elif record['eventName'] == "REMOVE":
      logger.debug("REMOVE event received")
      remove_evidence(membershipNumber)
      remove_references(membershipNumber)


def application_received(application):
  logger.debug("Sending application received")

  name = application['firstName']['S'] + " " + application['surname']['S']
  email = application['email']['S']
  membershipNumber = application['membershipNumber']['S']
  
  try:
    ses.send_templated_email(
      Source='"KSWP Portal" <portal@kswp.org.uk>',
      Destination={
        'ToAddresses': [
          '"'+name+'" <'+email+'>',
        ],
        'CcAddresses': [
          MEMBERS_EMAIL
        ]
      },
      ReplyToAddresses=[
        MEMBERS_EMAIL
      ],
      ReturnPath='bounces@kswp.org.uk',
      Template=APPLICATION_RECEIVED_TEMPLATE,
      TemplateData=json.dumps({
        'name': name,
        'membershipNumber': membershipNumber,
        'portalDomain': PORTAL_DOMAIN
      })
    )
  except Exception as e:
    logger.error(f"Unable to send {APPLICATION_RECEIVED_TEMPLATE} e-mail to {email} for {membershipNumber}: {str(e)}")
    raise e
  
  logger.info(f"{APPLICATION_RECEIVED_TEMPLATE} e-mail sent to {email} for {membershipNumber}")


def remove_evidence(membershipNumber):
  logger.debug("Deleting application evidence")

  try:
    s3.delete_object(
      Bucket=EVIDENCE_BUCKET_NAME,
      Key=f"{membershipNumber}.jpg"
    )
  except Exception as e:
    logger.error(f"Unable to delete evidence uploaded as part of application for {membershipNumber}: {str(e)}")
    return

  logger.info(f"Delete evidence uploaded as part of application for {membershipNumber}")


def remove_references(membershipNumber):
  logger.debug("Deleting references")

  table = dynamodb.Table(REFERENCES_TABLE)

  # List references
  try:
    toDelete = table.query(
      KeyConditionExpression=Key('membershipNumber').eq(membershipNumber)
    )
  except Exception as e:
    logger.error(f"Unable to get list of references to delete: {str(e)}")
    return
  
  logger.info(f"{len(toDelete['Items'])} references for {membershipNumber} found for deletion")

  deletedCount = 0
  for reference in toDelete['Items']:
    logger.debug(f"Deleting reference for {membershipNumber} from {reference['referenceEmail']}")

    # Delete references from DynamoDB
    try:
      table.delete_item(
        Key={
          'membershipNumber': reference['membershipNumber'],
          'referenceEmail': reference['referenceEmail']
        }
      )

      deletedCount += 1
    except Exception as e:
      logger.error(f"Unable to delete {reference['referenceEmail']} from DynamoDB: {str(e)}")
      continue
  

  logger.info(f"Deleted {deletedCount} references for {membershipNumber} ({len(toDelete['Items']) - deletedCount} errors)")
