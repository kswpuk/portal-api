import json
import boto3
from   boto3.dynamodb.conditions import Key
import datetime
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

TABLE_NAME = os.getenv('TABLE_NAME')
STATUS_INDEX_NAME = os.getenv('STATUS_INDEX_NAME')
EXPIRES_SOON_TEMPLATE = os.getenv('EXPIRES_SOON_TEMPLATE')
MEMBERSHIP_EXPIRED_TEMPLATE = os.getenv('MEMBERSHIP_EXPIRED_TEMPLATE')

logger.info(f"DynamoDB Table Name: {TABLE_NAME}")
logger.info(f"DynamoDB Status Index Name: {STATUS_INDEX_NAME}")
logger.info(f"Membership Expires Soon Template: {EXPIRES_SOON_TEMPLATE}")
logger.info(f"Membership Expired Template: {MEMBERSHIP_EXPIRED_TEMPLATE}")

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

def handler(event, context):
  table = dynamodb.Table(TABLE_NAME)

  currDate = datetime.date.today().isoformat()
  logger.info(f"Today's date: {currDate}")

  expiresSoonDate = (datetime.date.today() + datetime.timedelta(days=28)).isoformat()
  logger.info(f"Expires soon date: {expiresSoonDate}")

  # Find ACTIVE members who have an expiry date exactly 1 month in the future and send reminder
  
  expiresSoonEmailCount = 0
  expiresSoonEmailErrors = 0
  try:
    expireSoonMembers = table.query(
      IndexName=STATUS_INDEX_NAME,
      KeyConditionExpression=Key('status').eq('ACTIVE') & Key('membershipExpires').eq(expiresSoonDate)
    )
  except Exception as e:
    logger.error(f"Unable to get list of members who will expire soon: {str(e)}")
    expireSoonMembers = {'Items':[]}

  logger.info(f"{len(expireSoonMembers['Items'])} members found who expire on {expiresSoonDate} and will be sent a reminder")
  
  for expireSoonMember in expireSoonMembers['Items']:   
    # Send e-mail to members who will expire soon
    try:
      name = expireSoonMember.get('preferredName', expireSoonMember['firstName']) + " " + expireSoonMember['surname']
      ses.send_templated_email(
        Source='"QSWP Portal" <portal@qswp.org.uk>',
        Destination={
          'ToAddresses': [
            '"'+name+'" <'+expireSoonMember['email']+'>',
          ]
        },
        ReplyToAddresses=[
            '"QSWP Membership Coordinator" <members@qswp.org.uk>',
        ],
        ReturnPath='bounces@qswp.org.uk',
        Template=EXPIRES_SOON_TEMPLATE,
        TemplateData=json.dumps({
          'name': name,
          'expiryDate': expiresSoonDate
        })
      )

      expiresSoonEmailCount += 1
    except Exception as e:
      logger.error(f"Unable to send {EXPIRES_SOON_TEMPLATE} e-mail to {expireSoonMember['email']}: {str(e)}")
      expiresSoonEmailErrors += 1

  # Update ACTIVE members who have an expiry date in the past, and change to INACTIVE
  expiredCount = 0
  expiredErrors = 0
  expiredEmailCount = 0
  expiredEmailErrors = 0
  try:
    expiredActiveMembers = table.query(
      IndexName=STATUS_INDEX_NAME,
      KeyConditionExpression=Key('status').eq('ACTIVE') & Key('membershipExpires').lt(currDate)
    )
  except Exception as e:
    logger.error(f"Unable to get list of expired members: {str(e)}")
    expiredActiveMembers = {'Items':[]}
  
  logger.info(f"{len(expiredActiveMembers['Items'])} members found who expired before {currDate} and will be set to INACTIVE")


  for expiredActiveMember in expiredActiveMembers['Items']:
    logger.info(f"Member {expiredActiveMember['membershipNumber']} ({expiredActiveMember['firstName']} {expiredActiveMember['surname']}) expired on {expiredActiveMember['membershipExpires']}")
    try:
      table.update_item(
        Key={
          'membershipNumber': expiredActiveMember['membershipNumber']
        },
        UpdateExpression="SET #s = :status",
        ExpressionAttributeNames={
          "#s": "status"
        },
        ExpressionAttributeValues={
          ":status": "INACTIVE"
        }
      )

      expiredCount += 1
    except Exception as e:
      logger.error(f"Unable to update membership status of {expiredActiveMember['membershipNumber']}: {str(e)}")
      expiredErrors += 1
      continue
    
    # Send e-mail to members who have expired
    try:
      name = expiredActiveMember.get('preferredName', expiredActiveMember['firstName']) + " " + expiredActiveMember['surname']
      ses.send_templated_email(
        Source='"QSWP Portal" <portal@qswp.org.uk>',
        Destination={
          'ToAddresses': [
            '"'+name+'" <'+expiredActiveMember['email']+'>',
          ]
        },
        ReplyToAddresses=[
            '"QSWP Membership Coordinator" <members@qswp.org.uk>',
        ],
        ReturnPath='bounces@qswp.org.uk',
        Template=MEMBERSHIP_EXPIRED_TEMPLATE,
        TemplateData=json.dumps({
          'name': name
        })
      )

      expiredEmailCount += 1
    except Exception as e:
      logger.error(f"Unable to send {MEMBERSHIP_EXPIRED_TEMPLATE} e-mail to {expiredActiveMember['email']}: {str(e)}")
      expiredEmailErrors += 1
  
  logger.info(f"Membership expires soon e-mails sent: {expiresSoonEmailCount} ({expiresSoonEmailErrors} errors)")
  logger.info(f"ACTIVE members expired: {expiredCount} ({expiredErrors} errors)")
  logger.info(f"Membership expired e-mails sent: {expiredEmailCount} ({expiredEmailErrors} errors)")