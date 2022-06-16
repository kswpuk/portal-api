import boto3
import json
import logging
import hashlib
from   mailchimp_marketing import Client
from   mailchimp_marketing.api_client import ApiClientError
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

API_KEY_SECRET_NAME = os.getenv('API_KEY_SECRET_NAME')
APPLICATION_ACCEPTED_TEMPLATE = os.getenv('APPLICATION_ACCEPTED_TEMPLATE')
COGNITO_PHONE = (os.getenv('COGNITO_PHONE', 'false').lower() == "true")
MAILCHIMP_LIST_ID = os.getenv('MAILCHIMP_LIST_ID')
MAILCHIMP_SERVER_PREFIX = os.getenv('MAILCHIMP_SERVER_PREFIX')
MEMBERS_EMAIL = os.getenv('MEMBERS_EMAIL')
PHOTO_BUCKET_NAME = os.getenv('PHOTO_BUCKET_NAME')
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')
USER_POOL = os.getenv('USER_POOL')

MANAGER_GROUP = os.getenv('MANAGER_GROUP')
EVENTS_GROUP = os.getenv('EVENTS_GROUP')
MEMBERS_GROUP = os.getenv('MEMBERS_GROUP')
MONEY_GROUP = os.getenv('MONEY_GROUP')
MEDIA_GROUP = os.getenv('MEDIA_GROUP')
SOCIALS_GROUP = os.getenv('SOCIALS_GROUP')
COMMITTEE_GROUP = os.getenv('COMMITTEE_GROUP')
STANDARD_GROUP = os.getenv('STANDARD_GROUP')

logger.info(f"API_KEY_SECRET_NAME = {API_KEY_SECRET_NAME}")
logger.info(f"APPLICATION_ACCEPTED_TEMPLATE = {APPLICATION_ACCEPTED_TEMPLATE}")
logger.info(f"COGNITO_PHONE = {COGNITO_PHONE}")
logger.info(f"MAILCHIMP_LIST_ID = {MAILCHIMP_LIST_ID}")
logger.info(f"MAILCHIMP_SERVER_PREFIX = {MAILCHIMP_SERVER_PREFIX}")
logger.info(f"MEMBERS_EMAIL = {MEMBERS_EMAIL}")
logger.info(f"PHOTO_BUCKET_NAME = {PHOTO_BUCKET_NAME}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")
logger.info(f"USER_POOL = {USER_POOL}")

logger.info(f"MANAGER_GROUP = {MANAGER_GROUP}")
logger.info(f"EVENTS_GROUP = {EVENTS_GROUP}")
logger.info(f"MEMBERS_GROUP = {MEMBERS_GROUP}")
logger.info(f"MONEY_GROUP = {MONEY_GROUP}")
logger.info(f"MEDIA_GROUP = {MEDIA_GROUP}")
logger.info(f"SOCIALS_GROUP = {SOCIALS_GROUP}")
logger.info(f"COMMITTEE_GROUP = {COMMITTEE_GROUP}")
logger.info(f"STANDARD_GROUP = {STANDARD_GROUP}")

# AWS Clients
cognito = boto3.client('cognito-idp')
secrets = boto3.client('secretsmanager')
ses = boto3.client('ses')
s3 = boto3.client('s3')

# Mailchimp Client
try:
  mailchimp_api_key = json.loads(secrets.get_secret_value(
    SecretId=API_KEY_SECRET_NAME
  )['SecretString'])['mailchimp']

  mailchimp = Client()
  mailchimp.set_config({
    "api_key": mailchimp_api_key,
    "server": MAILCHIMP_SERVER_PREFIX
  })

  del mailchimp_api_key
except Exception as e:
  logger.error(f"Failed to initialize MailChimp client: {str(e)}")
  mailchimp = None

def handler(event, context):
  logger.debug(event)

  for record in event['Records']:
    if record['eventSource'] != "aws:dynamodb":
      logger.warning(f"Non-DynamoDB event found - skipping: {json.dumps(record)}")
      continue

    membershipNumber = record['dynamodb']['Keys']['membershipNumber']['S']
    logger.info(f"{record['eventName']} event for {membershipNumber}")

    if record['eventName'] == "INSERT":
      send_welcome_email(membershipNumber, record['dynamodb']['NewImage'])
      create_user(membershipNumber, record['dynamodb']['NewImage'])
      subscribe_to_mailchimp(membershipNumber, record['dynamodb']['NewImage'])
    elif record['eventName'] == "MODIFY":
      update_user(membershipNumber, record['dynamodb']['NewImage'], record['dynamodb']['OldImage'])
      update_user_groups(membershipNumber, record['dynamodb']['NewImage'], record['dynamodb']['OldImage'])
    elif record['eventName'] == "REMOVE":
      delete_user(membershipNumber)
      unsubscribe_from_mailchimp(membershipNumber, record['dynamodb']['OldImage'])
      delete_member_photo(membershipNumber)


def send_welcome_email(membershipNumber, newImage):
  try:
    ses.send_templated_email(
      Source='"QSWP Portal" <portal@qswp.org.uk>',
      Destination={
        'ToAddresses': [
          '"'+newImage['firstName']['S']+' '+newImage['surname']['S']+'" <'+newImage['email']['S']+'>',
        ]
      },
      ReplyToAddresses=[
        MEMBERS_EMAIL
      ],
      ReturnPath='bounces@qswp.org.uk',
      Template=APPLICATION_ACCEPTED_TEMPLATE,
      TemplateData=json.dumps({
        'firstName': newImage['firstName']['S'],
        'portalDomain': PORTAL_DOMAIN
      })
    )
  except Exception as e:
    logger.error(f"Unable to send {APPLICATION_ACCEPTED_TEMPLATE} e-mail to {membershipNumber} ({newImage['email']['S']}): {str(e)}")


def create_user(membershipNumber, newImage):
  userAttributes = []

  if 'email' in newImage and 'S' in newImage['email']:
    userAttributes.append({
      'Name': 'email',
      'Value': newImage['email']['S']
    })
    userAttributes.append({
      'Name': 'email_verified',
      'Value': 'true'
    })
  
  if 'telephone' in newImage and 'S' in newImage['telephone'] and COGNITO_PHONE:
    userAttributes.append({
      'Name': 'phone_number',
      'Value': newImage['telephone']['S']
    })
    userAttributes.append({
      'Name': 'phone_number_verified',
      'Value': 'true'
    })

  try:
    cognito.admin_create_user(
      UserPoolId=USER_POOL,
      Username=membershipNumber,
      UserAttributes=userAttributes,
      DesiredDeliveryMediums=["EMAIL"]
    )
  except Exception as e:
    logger.error(f"Unable to create user {membershipNumber} in Cognito: {str(e)}")
  
  # Add to STANDARD group
  try:
    cognito.admin_add_user_to_group(
      UserPoolId=USER_POOL,
      Username=membershipNumber,
      GroupName=STANDARD_GROUP
    )
  except Exception as e:
    logger.error(f"Unable to add user {membershipNumber} to group {STANDARD_GROUP}: {str(e)}")
  

def subscribe_to_mailchimp(membershipNumber, member):
  member_info = {
    "email_address": member['email']['S'],
    "status": "subscribed",
    "merge_fields": {
      "FNAME": member['firstName']['S'],
      "LNAME": member['surname']['S']
    }
  }

  try:
    response = mailchimp.lists.add_list_member(MAILCHIMP_LIST_ID, member_info)
    logger.info(f"{membershipNumber} ({member['email']['S']}) subscribed to MailChimp with id {response['id']}")
  
  except ApiClientError as e:
    logger.error(f"Unable to subscribe {membershipNumber} to MailChimp: {e.text}")
  
  except Exception as e:
    logger.error(f"Unable to subscribe {membershipNumber} to MailChimp: {str(e)}")


def update_user(membershipNumber, newImage, oldImage):
  cognito_changes = []
  mailchimp_changes = {}
  mailchimp_merge_fields = {}
  logMessage = []

  if 'email' in newImage and 'S' in newImage['email']:
    newEmail = newImage['email']['S']
    if oldImage.get('email', {}).get('S') != newEmail:
      cognito_changes.append({
        'Name': 'email',
        'Value': newEmail
      })
      cognito_changes.append({
        'Name': 'email_verified',
        'Value': 'true'
      })
      mailchimp_changes['email_address'] = newEmail
      logMessage.append(f"New e-mail: {newEmail}")

  if 'telephone' in newImage and 'S' in newImage['telephone'] and COGNITO_PHONE:
    newPhone = newImage['telephone']['S']
    if oldImage.get('telephone', {}).get('S') != newPhone:
      cognito_changes.append({
        'Name': 'phone_number',
        'Value': newPhone
      })
      cognito_changes.append({
        'Name': 'phone_number_verified',
        'Value': 'true'
      })
      logMessage.append(f"New phone number: {newPhone}")
  
  if 'firstName' in newImage and 'S' in newImage['firstName']:
    newFirstName = newImage['firstName']['S']
    if oldImage.get('firstName', {}).get('S') != newFirstName:
      mailchimp_merge_fields['FNAME'] = newFirstName
      logMessage.append(f"New first name: {newFirstName}")
  
  if 'surname' in newImage and 'S' in newImage['surname']:
    newSurname = newImage['surname']['S']
    if oldImage.get('surname', {}).get('S') != newSurname:
      mailchimp_merge_fields['LNAME'] = newSurname
      logMessage.append(f"New surname: {newSurname}")

  if len(mailchimp_merge_fields) > 0:
    mailchimp_changes['merge_fields'] = mailchimp_merge_fields

  if len(cognito_changes) == 0:
    logger.info("Changes don't require modifications to Cognito")
  else:
    try:
      cognito.admin_update_user_attributes(
        UserPoolId=USER_POOL,
        Username=membershipNumber,
        UserAttributes=cognito_changes
      )

      logger.info(f"Cognito profile for {membershipNumber} updated. {'; '.join(logMessage)}")
    except Exception as e:
      logger.error(f"Unable to update details for user {membershipNumber} in Cognito: {str(e)}")
  
  if len(mailchimp_changes) == 0:
    logger.info("Changes don't require modifications to MailChimp")
  else:
    try:
      response = mailchimp.lists.update_list_member(MAILCHIMP_LIST_ID, get_mailchimp_hash(oldImage['email']['S']), mailchimp_changes)
      logger.info(f"{membershipNumber} ({newImage['email']['S']}) updated in MailChimp with id {response['id']}")

    except ApiClientError as e:
      logger.error(f"Unable to update {membershipNumber} in MailChimp: {e.text}")
  
    except Exception as e:
      logger.error(f"Unable to update {membershipNumber} in MailChimp: {str(e)}")


def update_user_groups(membershipNumber, newImage, oldImage):
  oldRole = oldImage.get('role', {}).get('S')
  newRole = newImage.get('role', {}).get('S')

  if oldRole == newRole:
    logger.info("Changes don't require changes to Cognito groups")
    return
  
  oldRoleGroup = get_cognito_group(oldRole)
  newRoleGroup = get_cognito_group(newRole)

  if oldRoleGroup is not None:
    # Remove old role
    logger.info(f"Removing {membershipNumber} from Cognito group {oldRoleGroup}")
    try:
      cognito.admin_remove_user_from_group(
        UserPoolId=USER_POOL,
        Username=membershipNumber,
        GroupName=oldRoleGroup
      )
    except Exception as e:
      logger.error(f"Unable to remove user {membershipNumber} from group {oldRoleGroup}: {str(e)}")
  
  if newRoleGroup is not None:
    # Add new role
    logger.info(f"Adding {membershipNumber} to Cognito group {newRoleGroup}")
    try:
      cognito.admin_add_user_to_group(
        UserPoolId=USER_POOL,
        Username=membershipNumber,
        GroupName=newRoleGroup
      )
    except Exception as e:
      logger.error(f"Unable to add user {membershipNumber} to group {newRoleGroup}: {str(e)}")

  if oldRoleGroup is not None and newRoleGroup is None:
    # Remove from COMMITTEE group
    logger.info(f"Removing {membershipNumber} from Cognito group {COMMITTEE_GROUP}")
    try:
      cognito.admin_remove_user_from_group(
        UserPoolId=USER_POOL,
        Username=membershipNumber,
        GroupName=COMMITTEE_GROUP
      )
    except Exception as e:
      logger.error(f"Unable to remove user {membershipNumber} from group {COMMITTEE_GROUP}: {str(e)}")
  elif newRoleGroup is not None and oldRoleGroup is None:
    # Add to COMMITTEE group
    logger.info(f"Adding {membershipNumber} to Cognito group {COMMITTEE_GROUP}")
    try:
      cognito.admin_add_user_to_group(
        UserPoolId=USER_POOL,
        Username=membershipNumber,
        GroupName=COMMITTEE_GROUP
      )
    except Exception as e:
      logger.error(f"Unable to add user {membershipNumber} to group {COMMITTEE_GROUP}: {str(e)}")


def get_cognito_group(role):
  if role == "MANAGER":
    return MANAGER_GROUP
  elif role == "EVENTS":
    return EVENTS_GROUP
  elif role == "MEMBERS":
    return MEMBERS_GROUP
  elif role == "MONEY":
    return MONEY_GROUP
  elif role == "MEDIA":
    return MEDIA_GROUP
  elif role == "SOCIALS":
    return SOCIALS_GROUP
  else:
    return None


def delete_user(membershipNumber):
  try:
    cognito.admin_delete_user(
      UserPoolId=USER_POOL,
      Username=membershipNumber
    )

    logger.info(f"User {membershipNumber} deleted from Cognito")
  except Exception as e:
    logger.error(f"Unable to delete user {membershipNumber} from Cognito: {str(e)}")
  

def unsubscribe_from_mailchimp(membershipNumber, member):
  try:
    mailchimp.lists.delete_list_member(MAILCHIMP_LIST_ID, get_mailchimp_hash(member['email']['S']))
    logger.info(f"{membershipNumber} ({member['email']['S']}) deleted from MailChimp")
  
  except ApiClientError as e:
    logger.error(f"Unable to delete {membershipNumber} from MailChimp: {e.text}")
  
  except Exception as e:
    logger.error(f"Unable to delete {membershipNumber} from MailChimp: {str(e)}")


def get_mailchimp_hash(email):
  result = hashlib.md5(email.encode())
  return result.hexdigest()


def delete_member_photo(membershipNumber):
  try:
    s3.delete_objects(
      Bucket=PHOTO_BUCKET_NAME,
      Delete={
        "Objects": [
          { "Key": f"{membershipNumber}.jpg" },
          { "Key": f"{membershipNumber}.thumb.jpg" }
        ]
      }
    )
  except Exception as e:
    logger.error(f"Unable to delete photo for {membershipNumber}: {str(e)}")