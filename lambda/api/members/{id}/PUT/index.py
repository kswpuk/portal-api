import boto3
import json
import logging
import os
import phonenumbers
import re
import time
from ukpostcodeutils import validation
from validate_email import validate_email

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

TABLE_NAME = os.getenv('TABLE_NAME')
logger.info(f"DynamoDB Table Name: {TABLE_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
  logger.debug(f"Received Event: {event}")

  # Get membership number
  membershipNumber = event['pathParameters']['id']
  if membershipNumber is None:
    logger.warn("Unable to get membership number from path")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get membership number from path"
    }
  
  logger.info(f"Updating details for {membershipNumber}")

  # Do validation

  logger.debug(f"Validating input for {membershipNumber}...")

  member = json.loads(event['body'])
  validationErrors = []

  firstName = str(member.get("firstName")).strip()
  if not firstName:
    validationErrors.append("First name cannot be empty")
  
  surname = str(member.get("surname")).strip()
  if not surname:
    validationErrors.append("Surname cannot be empty")

  email = str(member.get("email")).strip()
  if not email:
    validationErrors.append("E-mail address cannot be empty")
  elif not validate_email(email, check_format=True, check_blacklist=True, check_dns=False, check_smtp=False):
    validationErrors.append("E-mail address is not valid, or the domain has been blacklisted")

  tel = str(member.get("telephone")).strip()
  if not tel:
    validationErrors.append("Telephone number cannot be empty")
  else:
    try:
      telephone = phonenumbers.parse(tel, "GB")
    except Exception as e:
      validationErrors.append("Telephone number could not be parsed: "+e.message)

    if not phonenumbers.is_valid_number(telephone):
      validationErrors.append("Telephone number is not valid")

  address = str(member.get("address")).strip()
  if not address:
    validationErrors.append("Address cannot be empty")
  
  postcode = re.sub(r"\s+", "", str(member.get("postcode")).upper())
  if not postcode:
    validationErrors.append("Postcode cannot be empty")
  elif not validation.is_valid_postcode(postcode):
    validationErrors.append("Postcode is not valid")

  emergencyContactName = str(member.get("emergencyContactName")).strip()
  if not emergencyContactName:
    validationErrors.append("Emergency contact name cannot be empty")

  emergencyContactTel = str(member.get("emergencyContactTelephone")).strip()
  if not emergencyContactTel:
    validationErrors.append("Emergency contact telephone number cannot be empty")
  else:
    try:
      emergencyContactTelephone = phonenumbers.parse(emergencyContactTel, "GB")
    except Exception as e:
      validationErrors.append(f"Emergency contact telephone number could not be parsed: {e.message}")

    if not phonenumbers.is_valid_number(emergencyContactTelephone):
      validationErrors.append("Emergency contact telephone number is not valid")
  
  if len(validationErrors) > 0:
    logger.warning(f"{len(validationErrors)} errors found during validation for {membershipNumber}: {validationErrors}")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "Errors found during validation",
        "detail": validationErrors
      })
    }
  else:
    logger.info(f"No errors found during validation for {membershipNumber}")

  # Update record in DynamoDB
  logger.debug(f"Sending update request for {membershipNumber}...")

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table(TABLE_NAME)

  response = table.update_item(Key = { "membershipNumber": membershipNumber },
    ConditionExpression = "membershipNumber = :membershipNumber",
    ReturnValues = "UPDATED_NEW",
    UpdateExpression = "SET firstName = :firstName, surname = :surname, preferredName = :preferredName, medicalInformation = :medicalInformation, dietaryRequirements = :dietaryRequirements, email = :email, telephone = :telephone, address = :address, postcode = :postcode, emergencyContactName = :emergencyContactName, emergencyContactTelephone = :emergencyContactTelephone, lastUpdated = :lastUpdated",
    ExpressionAttributeValues = {
      ":membershipNumber": membershipNumber,
      ":firstName": firstName,
      ":surname": surname,
      ":preferredName": str(member.get("preferredName")).strip(),
      ":medicalInformation": str(member.get("medicalInformation")).strip(),
      ":dietaryRequirements": str(member.get("dietaryRequirements")).strip(),
      ":email": email,
      ":telephone": phonenumbers.format_number(telephone, phonenumbers.PhoneNumberFormat.E164),
      ":address": address,
      ":postcode": postcode[:-3] + " " + postcode[-3:],
      ":emergencyContactName": emergencyContactName,
      ":emergencyContactTelephone": phonenumbers.format_number(emergencyContactTelephone, phonenumbers.PhoneNumberFormat.E164),
      ":lastUpdated": int(time.time())
    }
  )

  logger.debug(f"Server response: {response}")
  logger.info(f"Details updated for {membershipNumber}")

  return {
    "statusCode": 200,
    "headers": headers
  }