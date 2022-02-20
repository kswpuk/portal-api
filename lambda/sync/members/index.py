import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

USER_POOL = os.getenv('USER_POOL')
logger.info(f"Cognito User Pool ID: {USER_POOL}")

cognito = boto3.client('cognito-idp')

def handler(event, context):
  logger.debug(event)

  for record in event['Records']:
    if record['eventSource'] != "aws:dynamodb":
      logger.warning(f"Non-DynamoDB event found - skipping: {json.dumps(record)}")
      continue

    membershipNumber = record['dynamodb']['Keys']['membershipNumber']['S']
    logger.info(f"{record['eventName']} event for {membershipNumber}")

    if record['eventName'] == "INSERT":
      create_user(membershipNumber, record['dynamodb']['NewImage'])
    elif record['eventName'] == "MODIFY":
      update_user(membershipNumber, record['dynamodb']['NewImage'], record['dynamodb']['OldImage'])
    elif record['eventName'] == "REMOVE":
      delete_user(membershipNumber)

def create_user(membershipNumber, newImage):
  userAttributes = []

  if 'email' in newImage and 'S' in newImage['email']:
    userAttributes.append({
      'Name': 'email',
      'Value': newImage['email']['S']
    })
  
  if 'telephone' in newImage and 'S' in newImage['telephone']:
    userAttributes.append({
      'Name': 'phone_number',
      'Value': newImage['telephone']['S']
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

def update_user(membershipNumber, newImage, oldImage):
  changes = []
  logMessage = []

  if 'email' in newImage and 'S' in newImage['email']:
    newEmail = newImage['email']['S']
    if oldImage.get('email', {}).get('S') != newEmail:
      changes.append({
        'Name': 'email',
        'Value': newEmail
      })
      logMessage.append(f"New e-mail: {newEmail}")

  if 'telephone' in newImage and 'S' in newImage['telephone']:
    newPhone = newImage['telephone']['S']
    if oldImage.get('telephone', {}).get('S') != newPhone:
      changes.append({
        'Name': 'phone_number',
        'Value': newPhone
      })
      logMessage.append(f"New phone number: {newPhone}")

  if len(changes) == 0:
    logger.info("Changes don't require modifications to Cognito")
    return

  #TODO: Do we want to set the email and phone number as verified?
  try:
    cognito.admin_update_user_attributes(
      UserPoolId=USER_POOL,
      Username=membershipNumber,
      UserAttributes=changes
    )

    logger.info(f"Cognito profile for {membershipNumber} updated. {'; '.join(logMessage)}")
  except Exception as e:
    logger.error(f"Unable to update details for user {membershipNumber} in Cognito: {str(e)}")

def delete_user(membershipNumber):
  try:
    cognito.admin_delete_user(
      UserPoolId=USER_POOL,
      Username=membershipNumber
    )

    logger.info(f"User {membershipNumber} deleted from Cognito")
  except Exception as e:
    logger.error(f"Unable to delete user {membershipNumber} from Cognito: {str(e)}")