import boto3
from   datetime import date
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

APPLICATIONS_TABLE_NAME = os.getenv('APPLICATIONS_TABLE_NAME')
logger.info(f"APPLICATIONS_TABLE_NAME = {APPLICATIONS_TABLE_NAME}")

MEMBERS_TABLE_NAME = os.getenv('MEMBERS_TABLE_NAME')
logger.info(f"MEMBERS_TABLE_NAME = {MEMBERS_TABLE_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
applications_table = dynamodb.Table(APPLICATIONS_TABLE_NAME)
members_table = dynamodb.Table(MEMBERS_TABLE_NAME)

def handler(event, context):
  logger.debug(event)

  membershipNumber = event['pathParameters']['id']

  # Check there is an application

  logger.debug(f"Confirming {membershipNumber} has submitted an application")

  try:
    application_response = applications_table.get_item(
      Key={
        "membershipNumber": membershipNumber
      }
    )
  except Exception as e:
    logger.error(f"Unable to get application for {membershipNumber}: {str(e)}")
    raise e

  if 'Item' not in application_response or 'membershipNumber' not in application_response['Item']:
    return {
      "statusCode": 404,
      "headers": headers,
      "body": json.dumps({
        "message": "We have not received an application for this membership number"
      })
    }
  
  application = application_response["Item"]

  # Copy application to members table
  try:
    members_table.put_item(
      Item={
        "membershipNumber": membershipNumber,
        "firstName": application["firstName"],
        "surname": application["surname"],
        "dateOfBirth": application["dateOfBirth"],
        "email": application["email"],
        "telephone": application["telephone"],
        "address": application["address"],
        "postcode": application["postcode"],
        "lastUpdated": application["submittedAt"],
        "qsaReceived": application["qsaReceived"],
        "status": "INACTIVE",
        "joinDate": date.today().isoformat()
      }
    )
  except Exception as e:
    logger.error(f"Unable to approve application for {membershipNumber}: {str(e)}")
    raise e

  # Remove application from applications table
  try:
    applications_table.delete_item(
      Key={
        "membershipNumber": membershipNumber
      }
    )
  except Exception as e:
    logger.error(f"Unable to delete application for {membershipNumber}: {str(e)}")
    raise e
  
  logger.info(f"Application approved for {membershipNumber}")

  return {
    "statusCode": 200,
    "headers": headers
  }