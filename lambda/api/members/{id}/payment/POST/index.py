
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
PORTAL_DOMAIN = os.getenv('PORTAL_DOMAIN')
SUCCESS_URL = os.getenv('SUCCESS_URL')

logger.info(f"API_KEY_SECRET_NAME = {API_KEY_SECRET_NAME}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")
logger.info(f"PORTAL_DOMAIN = {PORTAL_DOMAIN}")
logger.info(f"SUCCESS_URL = {SUCCESS_URL}")

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
  membershipNumber = event['pathParameters']['id']
  if membershipNumber is None:
    logger.warn("Unable to get membership number from path")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get membership number from path"
    }

  logger.info(f"Getting membership details for {membershipNumber}")

  try:
    member = members_table.get_item(Key={'membershipNumber': membershipNumber})['Item']
  except Exception as e:
    logger.error(f"Unable to get member details for {membershipNumber}: {str(e)}")
    return {
      "statusCode": 404,
      "headers": headers,
      "body": "Member doesn't exist"
    }

  # Check membership has expired or is due to shortly
  expiry = datetime.date.fromisoformat(member['membershipExpires'])

  if expiry > (datetime.date.today() + datetime.timedelta(days=30)):
    logger.warn(f"Current expiry date is more than 30 days in the future")
    return {
      "statusCode": 400,
      "headers": headers,
      "body": "Current expiry date is more than 30 days in the future"
    }

  logger.info(f"Initializing Stripe Checkout session for {membershipNumber}")
  
  try:
    session = stripe.checkout.Session.create(
      customer_email=member['email'],
      line_items=[{
        'price_data': {
          'currency': 'gbp',
          'product_data': {
            'name': 'QSWP Membership',
            'description': 'Annual QSWP membership fee'
          },
          'unit_amount': 500,
        },
        'quantity': 1,
      }],
      mode='payment',
      success_url=SUCCESS_URL,
      cancel_url=f"https://{PORTAL_DOMAIN}/user/pay",
      metadata={
        'membershipNumber': membershipNumber,
        'memberName': f"{member['firstName']} {member['surname']}"
      }
    )
  except Exception as e:
    logger.error(f"Failed to create Stripe Checkout session for {membershipNumber}: {str(e)}")
    return {
      "statusCode": 404,
      "headers": headers,
      "body": "Failed to create Stripe Checkout session"
    }

  logger.debug(f"Response from Stripe: {session}")

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({
      "url": session.url
    })
  }
