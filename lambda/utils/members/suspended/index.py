
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

import boto3
import datetime
import os

# Configure logging
logger = Logger()

MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info("Initialising Lambda", extra={"environment_variables": {
  "MEMBERS_TABLE": MEMBERS_TABLE,
}})

# Set up AWS
dynamodb = boto3.resource('dynamodb')
members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):
  membership_numbers = event['membershipNumbers']
  if not isinstance(membership_numbers, list):
    membership_numbers = [membership_numbers]

  ret = dict()

  for m in membership_numbers:
    logger.info("Getting member", extra={"membership_number": m})
  
    try:
      member = members_table.get_item(
        Key={
          "membershipNumber": str(m)
        },
        ProjectionExpression="membershipNumber,suspended"
      )['Item']
    except Exception as e:
      logger.error("Unable to get member", extra={"membership_number": m})
      continue

    ret[m] = member.get("suspended", False)
  
  return ret