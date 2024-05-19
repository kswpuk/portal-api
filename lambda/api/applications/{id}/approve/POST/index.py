from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.data_classes import event_source, APIGatewayProxyEvent
from aws_lambda_powertools.utilities.typing import LambdaContext

import boto3
from   datetime import date
import json
import os
import time

logger = Logger()
metrics = Metrics()

APPLICATIONS_TABLE_NAME = os.getenv('APPLICATIONS_TABLE_NAME')
MEMBERS_TABLE_NAME = os.getenv('MEMBERS_TABLE_NAME')

logger.info("Initialising Lambda", extra={"environment_variables": {
  "APPLICATIONS_TABLE_NAME": APPLICATIONS_TABLE_NAME,
  "MEMBERS_TABLE_NAME": MEMBERS_TABLE_NAME
}})

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
applications_table = dynamodb.Table(APPLICATIONS_TABLE_NAME)
members_table = dynamodb.Table(MEMBERS_TABLE_NAME)

@event_source(data_class=APIGatewayProxyEvent)
@metrics.log_metrics
def handler(event: APIGatewayProxyEvent, context: LambdaContext):
  membershipNumber = event.path_parameters['id']
  logger.append_keys(membership_number=membershipNumber)

  # Check there is an application
  logger.debug("Confirming application exists")

  try:
    application_response = applications_table.get_item(
      Key={
        "membershipNumber": membershipNumber
      }
    )
  except Exception as e:
    logger.exception("Unable to get application")
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
    logger.exception("Unable to approve application")
    raise e

  # Remove application from applications table
  try:
    applications_table.delete_item(
      Key={
        "membershipNumber": membershipNumber
      }
    )
  except Exception as e:
    logger.exception("Unable to delete application")
    raise e

  # Calculate how long it took to approve the application
  submitted_at = int(application["submittedAt"])
  now = int(time.time())
  delay_s = now - submitted_at
  
  metrics.add_metric(name="ApplicationsApprovedCount", unit=MetricUnit.Count, value=1)
  metrics.add_metric(name="ApplicationsApprovalTime", unit=MetricUnit.Seconds, value=delay_s)

  logger.info("Application approved")

  return {
    "statusCode": 200,
    "headers": headers
  }