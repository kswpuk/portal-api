from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

import boto3
from   boto3.dynamodb.conditions import Attr
import datetime
import json
import os

# Configure logging
logger = Logger()

APPLICATIONS_TABLE = os.getenv('APPLICATIONS_TABLE')
REFERENCES_TABLE = os.getenv('REFERENCES_TABLE')

logger.info("Initialising Lambda", extra={"environment_variables": {
  "APPLICATIONS_TABLE": APPLICATIONS_TABLE,
  "REFERENCES_TABLE": REFERENCES_TABLE
}})

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

applications_table = dynamodb.Table(APPLICATIONS_TABLE)
references_table = dynamodb.Table(REFERENCES_TABLE)

def handler(event, context: LambdaContext):
  # Get data
  logger.debug("Scanning for all applications")
  try:
    applications = scan_table(applications_table)
  except Exception as e:
    logger.error("Unable to scan applications table", extra={"error": str(e)})
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to scan applications table"
    }

  logger.debug("Scanning for all references")
  try:
    references = scan_table(references_table, FilterExpression=Attr("submittedAt").gt(0))
  except Exception as e:
    logger.error("Unable to scan references table", extra={"error": str(e)})
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to scan references table"
    }

  # Process references
  logger.debug("Processing references")

  reference_status = {}
  for ref in references:
    status = reference_status.get(ref["membershipNumber"], {"scouting": None, "nonScouting": None, "fiveYears": None})

    relationship = ref.get("relationship", None)
    if relationship is None:
      continue

    accepted = "accepted" in ref and ref["accepted"]

    if accepted:
      status[relationship] = "ACCEPTED"
    elif status[relationship] != "ACCEPTED":
      status[relationship] = "SUBMITTED"
    
    moreThanFive = (ref.get("howLong", None) == "moreThan5")
    if moreThanFive:
      if accepted:
        status["fiveYears"] = "ACCEPTED"
      elif status["fiveYears"] != "ACCEPTED":
        status["fiveYears"] = "SUBMITTED"
    
    reference_status[ref["membershipNumber"]] = status

  # Combine references
  results = []
  for app in applications:
    results.append({
      **app,
      "submittedAt": int(app["submittedAt"]),
      "applicationStatus": reference_status.get(app["membershipNumber"], {"scouting": None, "nonScouting": None, "fiveYears": False})
    })

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(results)
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
