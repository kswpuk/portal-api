import boto3
from collections import Counter
import datetime
import json
import logging
import os
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):

  # Get members
  try:
    portal_members = scan_members()
  except Exception as e:
    logger.error(f"Unable to list members: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to list members"
    }

  statusCount = Counter([member['status'] for member in portal_members])
  timeCount = Counter([calculate_years(member['joinDate']) for member in portal_members])

  ageCount = {
    "UNDER_18": 0,
    "18_25": 0,
    "25_35": 0,
    "35_45": 0,
    "45_55": 0,
    "55_65": 0,
    "OVER_65": 0
  }
  ageActiveCount = ageCount.copy()
  ageInactiveCount = ageCount.copy()
  postcodesActive = []

  today = datetime.date.today()

  oldestDate = today
  newestDate = datetime.date.fromisoformat("1900-01-01")

  for member in portal_members:
    ageGroup = group_age(calculate_years(member['dateOfBirth']))
    ageCount[ageGroup] += 1
    if member['status'] == "ACTIVE":
      ageActiveCount[ageGroup] += 1
      postcodesActive.append(get_area(member['postcode']))
    elif member['status'] == "INACTIVE":
      ageInactiveCount[ageGroup] += 1
    
    joinDate = datetime.date.fromisoformat(member['joinDate'])
    if joinDate > newestDate:
      newestDate = joinDate

    if joinDate < oldestDate:
      oldestDate = joinDate

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps({
      "count": len(portal_members),
      "counts": {
        "status": statusCount,
        "time": timeCount,
        "age": ageCount,
        "ageActive": ageActiveCount,
        "ageInactive": ageInactiveCount,
        "postcodesActive": Counter(postcodesActive)
      },
      "newest": newestDate.isoformat(),
      "newestDays": (today - newestDate).days,
      "oldest": oldestDate.isoformat(),
      "oldestDays":  (today - oldestDate).days
    })
  }

def scan_members(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = members_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="dateOfBirth,joinDate,postcode,#s",
        ExpressionAttributeNames={
          "#s": "status"
        },
        **kwargs
      )
    else: 
      response = members_table.scan(
        ProjectionExpression="dateOfBirth,joinDate,postcode,#s",
        ExpressionAttributeNames={
          "#s": "status"
        },
        **kwargs
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results

def calculate_years(d):
  today = datetime.date.today()
  then = datetime.date.fromisoformat(d)

  return today.year - then.year - ((today.month, today.day) < (then.month, then.day))

def group_age(age):
  if age < 18:
    return "UNDER_18"
  elif age < 25:
    return "18_25"
  elif age < 35:
    return "25_35"
  elif age < 45:
    return "35_45"
  elif age < 55:
    return "45_55"
  elif age < 65:
    return "55_65"
  else:
    return "OVER_65"

def get_area(postcode):
  return re.split(r'[\d\s]', postcode)[0]