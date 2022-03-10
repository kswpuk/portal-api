import base64
import boto3
import io
import logging
import os
from PIL import Image, ImageOps

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

PHOTO_BUCKET_NAME = os.getenv('PHOTO_BUCKET_NAME')
logger.info(f"PHOTO_BUCKET_NAME = {PHOTO_BUCKET_NAME}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,PUT",
  "Access-Control-Allow-Origin": "*"
}

s3 = boto3.resource('s3')
photo_bucket = s3.Bucket(PHOTO_BUCKET_NAME)

def handler(event, context):

  # Get membership number
  membershipNumber = event['pathParameters']['id']
  if membershipNumber is None:
    logger.warn("Unable to get membership number from path")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to get membership number from path"
    }
  
  # Remove existing image if event['body'] is null
  if event['body'] is None or not event['body']:
    photo_bucket.delete_objects(Delete={
      'Objects': [
        {
          'Key': membershipNumber + ".jpg"
        }
      ]
    })

    return {
      "statusCode": 200,
      "headers": headers
    }
  
  logger.info(f"Updating photo for {membershipNumber}")

  try:
    photo = Image.open(io.BytesIO(base64.decodebytes(bytes(event['body'].split(",", 1)[1], "utf-8")))).convert("RGB")
  except Exception as e:
    logger.warning(f"Unable to open photo: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to open uploaded photo"
    }
  
  # Resize image if it's too large
  if photo.width > 1024 or photo.height > 1024:
    logger.debug(f"Resizing photo for {membershipNumber}")
    try:
      photo = ImageOps.contain(photo, (1024, 1024))
    except Exception as e:
      logger.warning(f"Unable to resize photo: {str(e)}")
      return {
        "statusCode": 500,
        "headers": headers,
        "body": "Unable to resize uploaded photo"
      }

  # Upload evidence to S3 as JPEG
  logger.debug(f"Uploading photo as JPEG to S3 bucket for {membershipNumber}")

  try:
    photo_b = io.BytesIO()
    photo.save(photo_b, "JPEG")
    photo_b.seek(0)

    photo_bucket.upload_fileobj(photo_b, membershipNumber + ".jpg", ExtraArgs={'ContentType': 'image/jpeg'})
  except Exception as e:
    logger.error(f"Failed to upload photo to S3: {str(e)}")

  logger.info(f"Photo updated for {membershipNumber}")

  return {
    "statusCode": 200,
    "headers": headers
  }