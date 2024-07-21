from aws_lambda_powertools import Logger
import boto3
from   boto3.dynamodb.conditions import Key
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

def handler(event, context):
  membership_number = event['pathParameters']['id']

  body = json.loads(event['body'])
  birth_date = body.get('dateOfBirth', None)

  if birth_date is None:
    return {
      "statusCode": 400,
      "headers": headers,
      "body": "Date of birth must be provided for validation purposes"
    }
  
  try:
    application = applications_table.get_item(Key={
      "membershipNumber": membership_number
    }, ProjectionExpression="membershipNumber,dateOfBirth,submittedAt")['Item']
  except Exception as e:
    return {
      "statusCode": 404,
      "headers": headers,
      "body": "Could not find application"
    }
  
  if birth_date != application['dateOfBirth']:
    return {
      "statusCode": 404,
      "headers": headers,
      "body": "Could not find application"  # Same error message here so we don't give away whether this application exists or not
    }

  try:
    references = get_references(membership_number)
  except Exception as e:
    return {
      "statusCode": 500,
      "headers": headers,
      "body": f"Unable to get references : {str(e)}"
    }
  
  status = {"scouting": None, "nonScouting": None, "fiveYears": None}
  for ref in references:
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
    
  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({
      "membershipNumber": membership_number,
      "submittedAt": int(application["submittedAt"]),
      "status": status
    })
  }

def get_references(membership_number):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = references_table.query(
        Select="SPECIFIC_ATTRIBUTES",
        ExclusiveStartKey=last_evaluated_key,
        KeyConditionExpression=Key('membershipNumber').eq(membership_number),
        ProjectionExpression="membershipNumber,accepted,relationship,howLong"
      )
    else: 
      response = references_table.query(
        Select="SPECIFIC_ATTRIBUTES",
        KeyConditionExpression=Key('membershipNumber').eq(membership_number),
        ProjectionExpression="membershipNumber,accepted,relationship,howLong"
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results
