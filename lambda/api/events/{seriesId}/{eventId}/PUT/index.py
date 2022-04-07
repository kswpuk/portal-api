import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_INSTANCE_TABLE_NAME = os.getenv('EVENT_INSTANCE_TABLE_NAME')
VALIDATION_ARN = os.getenv('VALIDATION_ARN')

logger.info(f"EVENT_INSTANCE_TABLE_NAME = {EVENT_INSTANCE_TABLE_NAME}")
logger.info(f"VALIDATION_ARN = {VALIDATION_ARN}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,POST",
  "Access-Control-Allow-Origin": "*"
}

dynamodb = boto3.resource('dynamodb')
event_instance_table = dynamodb.Table(EVENT_INSTANCE_TABLE_NAME)
lambda_client = boto3.client('lambda')

def handler(event, context):
  logger.debug(event)

  eventSeriesId = str(event['pathParameters']['seriesId']).strip().lower()
  eventId = str(event['pathParameters']['eventId']).strip().lower()

  # Check that the instance ID exists
  logger.debug(f"Checking event instance {eventSeriesId}/{eventId} exists")
  try:
    response = event_instance_table.get_item(
      Key={
        "eventSeriesId": eventSeriesId,
        "eventId": eventId,
      },
      ProjectionExpression="eventSeriesId,eventId"
    )

    if 'Item' not in response or 'eventId' not in response['Item']:
      return {
        "statusCode": 404,
        "headers": headers,
        "body": json.dumps({
          "message": f"Event {eventSeriesId}/{eventId} does not exist"
        })
      }
  except Exception as e:
    logger.error(f"Unable to check if {eventSeriesId}/{eventId} exists: {str(e)}")
    raise e

  # Do validation
  logger.debug(f"Validating input for {eventSeriesId}/{eventId}...")

  instance = json.loads(event['body'])
  instance["eventSeriesId"] = eventSeriesId
  instance["eventId"] = eventId

  instance["_allowPastDates"] = True

  try:
    validationResult = json.loads(lambda_client.invoke(
      FunctionName=VALIDATION_ARN,
      Payload=json.dumps(instance)
    )['Payload'].read())
  except Exception as e:
    logger.error(f"Unable to validate event {eventSeriesId}/{eventId}: {str(e)}")
    raise e

  if not validationResult["valid"]:
    logger.warning(f"{len(validationResult['errors'])} errors found during validation of event {eventSeriesId}/{eventId}: {validationResult['errors']}")
    return {
      "statusCode": 422,
      "headers": headers,
      "body": json.dumps({
        "message": "Errors found during validation",
        "detail": validationResult['errors']
      })
    }
  else:
    logger.info(f"No errors found during validation of event {eventSeriesId}/{eventId}")

  # Put records in DynamoDB
  logger.debug(f"Updating event {eventSeriesId}/{eventId}...")

  response = event_instance_table.update_item(
    Key={
        "eventSeriesId": eventSeriesId,
        "eventId": eventId
    },
    UpdateExpression="SET details=:details, #location=:location, postcode=:postcode, locationType=:locationType, registrationDate=:registrationDate, startDate=:startDate, endDate=:endDate, attendanceCriteria=:attendanceCriteria, attendanceLimit=:attendanceLimit",
    ExpressionAttributeNames={
      "#location": "location"
    },
    ExpressionAttributeValues={
      ":details": validationResult["event"]["details"],
      ":location": validationResult["event"]["location"],
      ":postcode": validationResult["event"]["postcode"],
      ":locationType": validationResult["event"]["locationType"],
      ":registrationDate": validationResult["event"]["registrationDate"],
      ":startDate": validationResult["event"]["startDate"],
      ":endDate": validationResult["event"]["endDate"],
      ":attendanceCriteria": validationResult["event"]["attendanceCriteria"],
      ":attendanceLimit": validationResult["event"]["attendanceLimit"],
    },
    ReturnValues = "NONE"
  )

  logger.debug(f"Server response: {response}")
  logger.info(f"Event {eventSeriesId}/{eventId} updated")

  return {
    "statusCode": 200,
    "headers": headers
  }