
import boto3
from   boto3.dynamodb.conditions import Attr
import datetime
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

COMMITTEE_GROUP = os.getenv('COMMITTEE_GROUP')
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"COMMITTEE_GROUP = {COMMITTEE_GROUP}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):
  # Get user groups
  try:
    groups = event['requestContext']['authorizer']['groups'].split(",")
  except:
    groups = []

  # Get data
  logger.debug("Scanning for all members")

  projectionExpression = "membershipNumber,firstName,preferredName,surname,#r,#s"
  expressionAttributeNames = {"#r": "role", "#s": "status"}
  try:
    
    if COMMITTEE_GROUP in groups:
      projectionExpression += ",email"

    members = scan_table(members_table, ProjectionExpression=projectionExpression, ExpressionAttributeNames=expressionAttributeNames)
  except Exception as e:
    logger.error(f"Unable to scan members table: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to scan members table"
    }

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(members)
  }

def scan_table(table, **kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = table.scan(
        ExclusiveStartKey=last_evaluated_key
        **kwargs
      )
    else: 
      response = table.scan(
        **kwargs
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results
