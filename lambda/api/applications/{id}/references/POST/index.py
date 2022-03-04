import base64
import boto3
import datetime
import io
import json
import logging
import os
import re
import time
from validate_email import validate_email

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

APPLICATIONS_TABLE_NAME = os.getenv('APPLICATIONS_TABLE_NAME')
logger.info(f"DynamoDB Application Table Name: {APPLICATIONS_TABLE_NAME}")

REFERENCES_TABLE_NAME = os.getenv('REFERENCES_TABLE_NAME')
logger.info(f"DynamoDB References Table Name: {REFERENCES_TABLE_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
applications_table = dynamodb.Table(APPLICATIONS_TABLE_NAME)
references_table = dynamodb.Table(REFERENCES_TABLE_NAME)

def handler(event, context):
  logger.debug(event)

  membershipNumber = event['pathParameters']['id']
  reference = json.loads(event['body'])

  # Check there is an application

  logger.debug(f"Confirming {membershipNumber} has submitted an application")

  applications_response = applications_table.get_item(
    Key={
      "membershipNumber": membershipNumber
    },
    AttributesToGet=[
      "membershipNumber"
    ]
  )
  if 'Item' not in applications_response or 'membershipNumber' not in applications_response['Item']:
    return {
      "statusCode": 404,
      "headers": headers,
      "body": json.dumps({
        "message": "We have not received an application for this membership number"
      })
    }
  
  # Check if we already have a reference from this e-mail for this member
  email = str(reference.get("email")).strip()
  references_response = references_table.get_item(
    Key={
      "membershipNumber": membershipNumber,
      "referenceEmail": email
    },
    AttributesToGet=[
      "membershipNumber",
      "relationship"
    ]
  )
  if 'Item' in references_response and 'relationship' in references_response['Item']:
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "We have already received a reference from this e-mail address for this application."
      })
    }

  logger.info(f"Submitting reference for {membershipNumber}")

  # Do validation

  logger.debug(f"Validating input for reference for {membershipNumber}...")

  validationErrors = []

  name = str(reference.get("name")).strip()
  if not name:
    validationErrors.append("Name cannot be empty")

  if not email:
    validationErrors.append("E-mail address cannot be empty")
  elif not validate_email(email, check_format=True, check_blacklist=True, check_dns=False, check_smtp=False):
    validationErrors.append("E-mail address is not valid, or the domain has been blacklisted")

  relationship = str(reference.get("relationship")).strip()
  if relationship != "scouting" and relationship != "nonScouting":
    validationErrors.append("Relationship is not an expected value")

  capacityKnown = str(reference.get("capacityKnown")).strip()
  if not capacityKnown:
    validationErrors.append("Capacity Known cannot be empty")

  howLong = str(reference.get("howLong")).strip()
  if howLong != "lessThan5" and howLong != "moreThan5":
    validationErrors.append("How Long is not an expected value")

  notConsidered = str(reference.get("notConsidered")).strip()
  if notConsidered != "no" and howLong != "yes":
    validationErrors.append("Not Considered is not an expected value")
  else:
    # Convert to a boolean
    notConsidered = (notConsidered == "yes")

  statementOfSupport = str(reference.get("statementOfSupport")).strip()
  if not statementOfSupport:
    validationErrors.append("Statement of Support cannot be empty")
  
  maturity = int(reference.get("maturity", "0"))
  if not (maturity >= 1 and maturity <= 5):
    validationErrors.append("Maturity must be between 1 and 5")
  
  responsibility = int(reference.get("responsibility", "0"))
  if not (responsibility >= 1 and responsibility <= 5):
    validationErrors.append("Responsibility must be between 1 and 5")
  
  selfMotivation = int(reference.get("selfMotivation", "0"))
  if not (selfMotivation >= 1 and selfMotivation <= 5):
    validationErrors.append("Self-motivation must be between 1 and 5")
  
  motivateOthers = int(reference.get("motivateOthers", "0"))
  if not (motivateOthers >= 1 and motivateOthers <= 5):
    validationErrors.append("Ability to Motivate Others must be between 1 and 5")
  
  commitment = int(reference.get("commitment", "0"))
  if not (commitment >= 1 and commitment <= 5):
    validationErrors.append("Commitment must be between 1 and 5")
  
  trustworthiness = int(reference.get("trustworthiness", "0"))
  if not (trustworthiness >= 1 and trustworthiness <= 5):
    validationErrors.append("Trustworthiness must be between 1 and 5")
  
  workWithAdults = int(reference.get("workWithAdults", "0"))
  if not (workWithAdults >= 1 and workWithAdults <= 5):
    validationErrors.append("Ability to Work with Adults must be between 1 and 5")
  
  respectForOthers = int(reference.get("respectForOthers", "0"))
  if not (respectForOthers >= 1 and respectForOthers <= 5):
    validationErrors.append("Respect for Others must be between 1 and 5")

  if len(validationErrors) > 0:
    logger.warning(f"{len(validationErrors)} errors found during validation of reference for {membershipNumber}: {validationErrors}")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "Errors found during validation",
        "detail": validationErrors
      })
    }
  else:
    logger.info(f"No errors found during validation of reference for {membershipNumber}")

  # Put records in DynamoDB
  logger.debug(f"Saving reference for {membershipNumber}...")

  references_table.put_item(
    Item={
      "membershipNumber": membershipNumber,
      "referenceEmail": email,
      "referenceName": name,
      "relationship": relationship,
      "capacityKnown": capacityKnown,
      "howLong": howLong,
      "notConsidered": notConsidered,
      "statementOfSupport": statementOfSupport,
      "maturity": maturity,
      "responsibility": responsibility,
      "selfMotivation": selfMotivation,
      "motivateOthers": motivateOthers,
      "commitment": commitment,
      "trustworthiness": trustworthiness,
      "workWithAdults": workWithAdults,
      "respectForOthers": respectForOthers,
      "submittedAt": int(time.time())
    },
    ConditionExpression = "attribute_not_exists(submittedAt)",   # If this already exists, then we've already received a reference from this e-mail for this person
    ReturnValues = "NONE"
  )

  logger.info(f"Reference submitted for {membershipNumber}")

  return {
    "statusCode": 200,
    "headers": headers
  }