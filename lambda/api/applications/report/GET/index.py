import boto3
from collections import Counter
import datetime
import json
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

APPLICATIONS_TABLE = os.getenv('APPLICATIONS_TABLE')
REFERENCES_TABLE = os.getenv('REFERENCES_TABLE')

logger.info(f"APPLICATIONS_TABLE = {APPLICATIONS_TABLE}")
logger.info(f"REFERENCES_TABLE = {REFERENCES_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

applications_table = dynamodb.Table(APPLICATIONS_TABLE)
references_table = dynamodb.Table(REFERENCES_TABLE)

def handler(event, context):
  # Get applications
  try:
    applications = scan_applications()
  except Exception as e:
    logger.error(f"Unable to get applications: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get applications"
    }

  postcodeCount = Counter([get_area(app['postcode']) for app in applications])
  
  oldestTimestamp = datetime.datetime.now().timestamp()
  newestTimestamp = 0

  for app in applications:    
    if app['submittedAt'] > newestTimestamp:
      newestTimestamp = app['submittedAt']

    if app['submittedAt'] < oldestTimestamp:
      oldestTimestamp = app['submittedAt']

  newestDate = datetime.datetime.fromtimestamp(oldestTimestamp).date()
  oldestDate = datetime.datetime.fromtimestamp(newestTimestamp).date()
  today = datetime.date.today()

  # TODO: Application status

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({
      "count": len(applications),
      "counts": {
        "postcode": postcodeCount
      },
      "newest": newestDate.isoformat(),
      "newestDays": (today - newestDate).days,
      "oldest": oldestDate.isoformat(),
      "oldestDays":  (today - oldestDate).days
    })
  }

def scan_applications(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = applications_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="postcode,submittedAt",
        **kwargs
      )
    else: 
      response = applications_table.scan(
        ProjectionExpression="postcode,submittedAt",
        **kwargs
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results

def get_area(postcode):
  return postcode[:-3].strip().upper()