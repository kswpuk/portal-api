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
DELETED_SOON_TEMPLATE = os.getenv('DELETED_SOON_TEMPLATE')
ACCOUNT_DELETED_TEMPLATE = os.getenv('ACCOUNT_DELETED_TEMPLATE')

GRACE_PERIOD_DAYS = 730 # 2 years

logger.info(f"DynamoDB Table Name: {TABLE_NAME}")
logger.info(f"DynamoDB Status Index Name: {STATUS_INDEX_NAME}")
logger.info(f"Account Deleted Soon Template: {DELETED_SOON_TEMPLATE}")
logger.info(f"Account Deleted Template: {ACCOUNT_DELETED_TEMPLATE}")

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

def handler(event, context):
  table = dynamodb.Table(TABLE_NAME)

  currDate = datetime.date.today().isoformat()
  logger.info(f"Today's date: {currDate}")

  expiredDate = datetime.date.today() - datetime.timedelta(days=GRACE_PERIOD_DAYS)

  soon60Days = expiredDate + datetime.timedelta(days=60)
  soon30Days = expiredDate + datetime.timedelta(days=30)
  soon3Days = expiredDate + datetime.timedelta(days=3)

  logger.info(f"Membership expired date for deletion: {expiredDate.isoformat()}")
  logger.info(f"Membership expired dates for reminders: {soon60Days.isoformat()}, {soon30Days.isoformat()}, {soon3Days.isoformat()}")

  # Send out reminders

  reminderEmailCount = 0
  reminderEmailErrors = 0

  r = reminders(soon60Days, table)
  reminderEmailCount += r[0]
  reminderEmailErrors += r[1]

  r = reminders(soon30Days, table)
  reminderEmailCount += r[0]
  reminderEmailErrors += r[1]

  r = reminders(soon3Days, table)
  reminderEmailCount += r[0]
  reminderEmailErrors += r[1]

  # Delete accounts

  deletedCount = 0
  deletedErrors = 0
  deletedEmailCount = 0
  deletedEmailErrors = 0

  try:
    toDelete = table.query(
      IndexName=STATUS_INDEX_NAME,
      KeyConditionExpression=Key('status').eq('INACTIVE') & Key('membershipExpires').lt(expiredDate.isoformat())
    )
  except Exception as e:
    logger.error(f"Unable to get list of members to delete: {str(e)}")
    toDelete = {'Items':[]}
  
  logger.info(f"{len(toDelete['Items'])} accounts found for deletion, which expired before {expiredDate.isoformat()}")


  for member in toDelete['Items']:
    logger.info(f"Inactive member {member['membershipNumber']} ({member['firstName']} {member['surname']}) expired on {member['membershipExpires']} - account will be deleted")

    # Delete accounts from DynamoDB
    try:
      table.delete_item(
        Key={
          'membershipNumber': member['membershipNumber']
        }
      )

      deletedCount += 1
    except Exception as e:
      logger.error(f"Unable to delete {member['membershipNumber']} from DynamoDB: {str(e)}")
      deletedErrors += 1
      continue
  
    # Don't need to delete accounts from Cognito, this will be done by DynamoDB Streams and Lambda

    # Send e-mail to members who have expired
    try:
      name = member.get('preferredName', member['firstName']) + " " + member['surname']
      ses.send_templated_email(
        Source='"QSWP Portal" <portal@qswp.org.uk>',
        Destination={
          'ToAddresses': [
            '"'+name+'" <'+member['email']+'>',
          ]
        },
        ReplyToAddresses=[
            '"QSWP Membership Coordinator" <members@qswp.org.uk>',
        ],
        ReturnPath='bounces@qswp.org.uk',
        Template=ACCOUNT_DELETED_TEMPLATE,
        TemplateData=json.dumps({
          'name': name
        })
      )

      deletedEmailCount += 1
    except Exception as e:
      logger.error(f"Unable to send {ACCOUNT_DELETED_TEMPLATE} e-mail to {member['email']}: {str(e)}")
      deletedEmailErrors += 1

  logger.info(f"Account deleted soon e-mails sent: {reminderEmailCount} ({reminderEmailErrors} errors)")
  logger.info(f"Accounts deleted from DynamoDB: {deletedCount} ({deletedErrors} errors)")
  logger.info(f"Account deleted e-mails sent: {deletedEmailCount} ({deletedEmailErrors} errors)")


def reminders(expiredDate, table):
  try:
    reminderMembers = table.query(
      IndexName=STATUS_INDEX_NAME,
      KeyConditionExpression=Key('status').eq('INACTIVE') & Key('membershipExpires').eq(expiredDate.isoformat())
    )
  except Exception as e:
    logger.error(f"Unable to get list of members who expired on {expiredDate.isoformat()}: {str(e)}")
    reminderMembers = {'Items':[]}

  logger.info(f"{len(reminderMembers['Items'])} accounts found for reminder e-mails, which expired on {expiredDate.isoformat()}")

  reminderEmailCount = 0
  reminderEmailErrors = 0

  for reminderMember in reminderMembers['Items']:   
    # Send e-mail to members who will expire soon
    try:
      name = reminderMember.get('preferredName', reminderMember['firstName']) + " " + reminderMember['surname']
      ses.send_templated_email(
        Source='"QSWP Portal" <portal@qswp.org.uk>',
        Destination={
          'ToAddresses': [
            '"'+name+'" <'+reminderMember['email']+'>',
          ]
        },
        ReplyToAddresses=[
            '"QSWP Membership Coordinator" <members@qswp.org.uk>',
        ],
        ReturnPath='bounces@qswp.org.uk',
        Template=DELETED_SOON_TEMPLATE,
        TemplateData=json.dumps({
          'name': name,
          'deletionDate': (expiredDate + datetime.timedelta(days=GRACE_PERIOD_DAYS)).isoformat()
        })
      )

      reminderEmailCount += 1
    except Exception as e:
      logger.error(f"Unable to send {DELETED_SOON_TEMPLATE} e-mail to {reminderMember['email']}: {str(e)}")
      reminderEmailErrors += 1

  return (reminderEmailCount, reminderEmailErrors)