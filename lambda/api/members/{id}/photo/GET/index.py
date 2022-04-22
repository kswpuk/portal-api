import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EXPIRATION = int(os.getenv("EXPIRATION", "3600"))
PHOTO_BUCKET_NAME = os.getenv("PHOTO_BUCKET_NAME")

logger.info(f"EXPIRATION = {EXPIRATION}")
logger.info(f"PHOTO_BUCKET_NAME = {PHOTO_BUCKET_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

s3 = boto3.client("s3")

def handler(event, context):

  # Get membership number
  membershipNumber = event["pathParameters"]["id"]
  if membershipNumber is None:
    logger.warn("Unable to get membership number from path")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get membership number from path"
    }

  # Check file exists
  key = membershipNumber + ".jpg"

  found = False
  try:
    response = s3.list_objects_v2(
      Bucket=PHOTO_BUCKET_NAME,
      Prefix=key,
    )

    for obj in response.get('Contents', []):
      if obj['Key'] == key:
        found = True
        break
  except Exception as e:
    logger.error(f"Failed to check file exists: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Failed to check file exists"
    }
  
  if not found:
    return {
      "statusCode": 404,
      "headers": headers
    }

  # Generate presigned URL
  try:
    url = s3.generate_presigned_url("get_object", ExpiresIn=EXPIRATION, Params={
      "Bucket": PHOTO_BUCKET_NAME,
      "Key": key
    })
  except Exception as e:
    logger.error(f"Failed to generate presigned URL: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Failed to generate presigned URL"
    }

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({"url": url})
  }