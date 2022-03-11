
import boto3
import datetime
import json
import logging
import os
import stripe

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

API_KEY_SECRET_NAME = os.getenv('API_KEY_SECRET_NAME')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"API_KEY_SECRET_NAME = {API_KEY_SECRET_NAME}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')
secrets = boto3.client('secretsmanager')

members_table = dynamodb.Table(MEMBERS_TABLE)

# Get Stripe
try:
  stripe.api_key = json.loads(secrets.get_secret_value(
    SecretId=API_KEY_SECRET_NAME
  )['SecretString'])['stripe']
except Exception as e:
  logger.error(f"Failed to get Stripe secret key from Secrets Manager: {str(e)}")
  stripe.api_key = None

def handler(event, context):
  session_id = event['pathParameters']['session']
  if session_id is None:
    logger.warn("Unable to get session from path")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get session from path"
    }

  logger.info(f"Getting Stripe session details for {session_id}")

  try:
    session = stripe.checkout.Session.retrieve(session_id)
  except Exception as e:
    logger.error(f"Failed to get Stripe session details: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Failed to get Stripe session details"
    } 

  logger.debug(f"Session details: {session}")

  session_metadata = session['metadata']
  
  logger.info(f"Getting member details for {session_metadata['membershipNumber']}")

  # Get current expiry date
  try:
    member = members_table.get_item(
      Key={"membershipNumber": session_metadata['membershipNumber']},
      AttributesToGet=[
        'membershipExpires'
      ]
    )['Item']
  except Exception as e:
    logger.error(f"Failed to get current expiry date: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Failed to get current expiry date"
    }
  
  today = datetime.date.today()
  expiry = datetime.date.fromisoformat(member['membershipExpires'])

  # Check expiry isn't too far in future to prevent replay attacks
  if expiry > (today + datetime.timedelta(days=30)):
    logger.warn(f"Replay attack detected (current expiry date is more than 30 days in the future) - membership status will not be updated")
    return {
      "statusCode": 400,
      "headers": headers,
      "body": "Replay attack detected (current expiry date is more than 30 days in the future) - membership status will not be updated"
    }
  
  if expiry < today:
    newExpiry = today + datetime.timedelta(days=365)
  else:
    newExpiry = expiry + datetime.timedelta(days=365)

  logger.info(f"Current expiry date for {session_metadata['membershipNumber']} = {expiry}")
  logger.info(f"New expiry date for {session_metadata['membershipNumber']} = {newExpiry}")

  logger.info(f"Updating membership status for {session_metadata['membershipNumber']}")

  try:
    members_table.update_item(
      Key={"membershipNumber": session_metadata['membershipNumber']},
      UpdateExpression="SET #s = :status, membershipExpires = :expires",
      ExpressionAttributeNames={
        "#s": "status"
      },
      ExpressionAttributeValues={
        ":status": "ACTIVE",
        ":expires": newExpiry.isoformat()
      }
    )
  except Exception as e:
    logger.error(f"Failed to update membership status: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Failed to update membership status"
    }
  
  logger.info(f"Membership for {session_metadata['membershipNumber']} updated")

  redir_headers = headers
  redir_headers['Location'] = "https://portal.qswp.org.uk/user/pay"

  return {
    "statusCode": 303,
    "headers": redir_headers
  }
