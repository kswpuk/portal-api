import base64
import boto3
import datetime
import io
import json
import logging
import os
import phonenumbers
from PIL import Image
import re
import time
from ukpostcodeutils import validation
from validate_email import validate_email

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

APPLICATIONS_TABLE_NAME = os.getenv('APPLICATIONS_TABLE_NAME')
logger.info(f"DynamoDB Application Table Name: {APPLICATIONS_TABLE_NAME}")

MEMBERS_TABLE_NAME = os.getenv('MEMBERS_TABLE_NAME')
logger.info(f"DynamoDB Member Table Name: {MEMBERS_TABLE_NAME}")

REFERENCES_TABLE_NAME = os.getenv('REFERENCES_TABLE_NAME')
logger.info(f"DynamoDB References Table Name: {REFERENCES_TABLE_NAME}")

EVIDENCE_BUCKET_NAME = os.getenv('EVIDENCE_BUCKET_NAME')
logger.info(f"S3 Evidence Bucket Name: {EVIDENCE_BUCKET_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
applications_table = dynamodb.Table(APPLICATIONS_TABLE_NAME)
members_table = dynamodb.Table(MEMBERS_TABLE_NAME)
references_table = dynamodb.Table(REFERENCES_TABLE_NAME)

s3 = boto3.resource('s3')
evidence_bucket = s3.Bucket(EVIDENCE_BUCKET_NAME)

def handler(event, context):
  logger.debug(event)

  membershipNumber = str(event['pathParameters']['id']).strip().lstrip('0')

  # Check this number isn't already in use!

  logger.debug(f"Confirming {membershipNumber} has not previously submitted an application, and isn't already a member...")

  applications_response = applications_table.get_item(
    Key={
      "membershipNumber": membershipNumber
    },
    AttributesToGet=[
      "membershipNumber"
    ]
  )
  if 'Item' in applications_response and 'membershipNumber' in applications_response['Item']:
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "We have already received an application for this membership number"
      })
    }

  members_response = members_table.get_item(
    Key={
      "membershipNumber": membershipNumber
    },
    AttributesToGet=[
      "membershipNumber"
    ]
  )
  if 'Item' in members_response and 'membershipNumber' in members_response['Item']:
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "This membership number belongs to an existing member or the QSWP"
      })
    }


  logger.info(f"Submitting application for {membershipNumber}")

  # Do validation

  logger.debug(f"Validating input for {membershipNumber}...")

  validationErrors = []
  application = json.loads(event['body'])

  if not membershipNumber:
    validationErrors.append("Membership number cannot be empty")
  elif not membershipNumber.isnumeric():
    validationErrors.append("Membership number must be a number")

  firstName = str(application.get("firstName")).strip()
  if not firstName: #TODO: firstName will actually be None here if firstName is empty... Use .get("")?
    validationErrors.append("First name cannot be empty")
  
  surname = str(application.get("surname")).strip()
  if not surname:
    validationErrors.append("Surname cannot be empty")

  if application.get("dateOfBirth") is None:
    validationErrors.errors("Date of Birth cannot be empty")
    dob = None
  else:
    dob = datetime.date.fromisoformat(application.get("dateOfBirth"))
    if datetime.datetime.now().year - dob.year < 18:
      validationErrors.append("You must be at least 18 to join the QSWP")

  email = str(application.get("email")).strip().lower()
  if not email:
    validationErrors.append("E-mail address cannot be empty")
  elif not validate_email(email, check_format=True, check_blacklist=True, check_dns=False, check_smtp=False):
    validationErrors.append("E-mail address is not valid, or the domain has been blacklisted")

  tel = str(application.get("telephone")).strip()
  if not tel:
    validationErrors.append("Telephone number cannot be empty")
  else:
    try:
      telephone = phonenumbers.parse(tel, "GB")
    except Exception as e:
      validationErrors.append("Telephone number could not be parsed: "+e.message)

    if not phonenumbers.is_valid_number(telephone):
      validationErrors.append("Telephone number is not valid")

  address = str(application.get("address")).strip()
  if not address:
    validationErrors.append("Address cannot be empty")
  
  postcode = re.sub("\s+", "", str(application.get("postcode")).upper())
  if not postcode:
    validationErrors.append("Postcode cannot be empty")
  elif not validation.is_valid_postcode(postcode):
    validationErrors.append("Postcode is not valid")
  
  qsaReceived = str(application.get("qsaReceived")).strip()
  if not qsaReceived:
    validationErrors.append("Month you received your Queen's Scout Award cannot be empty")
  elif not re.match("^(19|20)[0-9]{2}-(0[1-9]|1[0-2])$", qsaReceived):
    validationErrors.append("Month you received your Queen's Scout Award is not valid")

  try:
    evidence = Image.open(io.BytesIO(base64.decodebytes(bytes(application.get("evidence").split(",", 1)[1], "utf-8")))).convert("RGB")
  except Exception as e:
    logger.warning(f"Unable to open evidence as image: {str(e)}")
    validationErrors.append("Unable to read evidence as image")

  srName = str(application.get("srName")).strip()
  if not srName:
    validationErrors.append("Scout reference name cannot be empty")
  
  srEmail = str(application.get("srEmail")).strip().lower()
  if not srEmail:
    validationErrors.append("Scout reference e-mail address cannot be empty")
  elif not validate_email(srEmail, check_format=True, check_blacklist=True, check_dns=False, check_smtp=False):
    validationErrors.append("Scout reference e-mail address is not valid, or the domain has been blacklisted")

  nsrName = str(application.get("nsrName")).strip()
  if not nsrName:
    validationErrors.append("Non-Scout reference name cannot be empty")
  
  nsrEmail = str(application.get("nsrEmail")).strip().lower()
  if not nsrEmail:
    validationErrors.append("Non-Scout reference e-mail address cannot be empty")
  elif not validate_email(nsrEmail, check_format=True, check_blacklist=True, check_dns=False, check_smtp=False):
    validationErrors.append("Non-Scout reference e-mail address is not valid, or the domain has been blacklisted")
  
  if srEmail == email:
    validationErrors.append("Scout reference cannot use your e-mail address")
  
  if nsrEmail == email:
    validationErrors.append("Non-Scout reference cannot use your e-mail address")

  if srEmail == nsrEmail:
    validationErrors.append("Scout reference and non-Scout reference cannot use the same e-mail address")

  if len(validationErrors) > 0:
    logger.warning(f"{len(validationErrors)} errors found during validation of application for {membershipNumber}: {validationErrors}")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "Errors found during validation",
        "detail": validationErrors
      })
    }
  else:
    logger.info(f"No errors found during validation of application for {membershipNumber}")

  # Put records in DynamoDB
  logger.debug(f"Submitting application for {membershipNumber}...")

  response = applications_table.put_item(
    Item={
      "membershipNumber": membershipNumber,
      "firstName": firstName,
      "surname": surname,
      "dateOfBirth": dob.isoformat(),
      "email": email,
      "telephone": phonenumbers.format_number(telephone, phonenumbers.PhoneNumberFormat.E164),
      "address": address,
      "postcode": postcode[:-3] + " " + postcode[-3:],
      "qsaReceived": qsaReceived,
      "submittedAt": int(time.time())
    },
    ConditionExpression = "attribute_not_exists(membershipNumber)",
    ReturnValues = "NONE"
  )

  logger.debug(f"Server response (application): {response}")

  response = references_table.put_item(
    Item={
      "membershipNumber": membershipNumber,
      "referenceEmail": srEmail,
      "referenceName": srName
    },
    ReturnValues = "NONE"
  )
  logger.debug(f"Server response (Scout reference): {response}")

  response = references_table.put_item(
    Item={
      "membershipNumber": membershipNumber,
      "referenceEmail": nsrEmail,
      "referenceName": nsrName
    },
    ReturnValues = "NONE"
  )
  logger.debug(f"Server response (non-Scout reference): {response}")

  # Upload evidence to S3 as JPEG
  logger.debug(f"Uploading evidence as JPEG to S3 bucket for {membershipNumber}")

  try:
    evidence_b = io.BytesIO()
    evidence.save(evidence_b, "JPEG")
    evidence_b.seek(0)

    evidence_bucket.upload_fileobj(evidence_b, membershipNumber + ".jpg", ExtraArgs={'ContentType': 'image/jpeg'})
  except Exception as e:
    logger.error(f"Failed to upload evidence to S3: {str(e)}")

  logger.info(f"Application submitted for {membershipNumber}")

  return {
    "statusCode": 200,
    "headers": headers
  }