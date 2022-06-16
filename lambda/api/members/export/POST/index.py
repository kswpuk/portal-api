
import boto3
from   boto3.dynamodb.conditions import Attr, Key
import csv
import datetime
from   io import StringIO
import json
import logging
import os
import phonenumbers


# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

ALLOCATIONS_TABLE = os.getenv('ALLOCATIONS_TABLE')
FIELD_NAMES = os.getenv('FIELD_NAMES', "membershipNumber,firstName,preferredName,surname").split(",")
MEMBERS_TABLE = os.getenv('MEMBERS_TABLE')

logger.info(f"ALLOCATIONS_TABLE = {ALLOCATIONS_TABLE}")
logger.info(f"FIELD_NAMES = {FIELD_NAMES}")
logger.info(f"MEMBERS_TABLE = {MEMBERS_TABLE}")

headers = {
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "OPTIONS,GET",
  "Access-Control-Allow-Origin": "*",
  "Content-Type": "text/csv"
}

# Set up AWS
dynamodb = boto3.resource('dynamodb')

allocations_table = dynamodb.Table(ALLOCATIONS_TABLE)
members_table = dynamodb.Table(MEMBERS_TABLE)

def handler(event, context):
  body = json.loads(event.get('body', '{}'))

  combinedEventId = body.get('combinedEventId', None)
  members = body.get('members', [])

  member_information = []
  field_names = FIELD_NAMES.copy()

  # If 'event' provided and no list of members, return all members for that event with allocation information for that event
  if combinedEventId is not None and len(members) == 0:
    allocations = get_allocations(combinedEventId)

    members = list(allocations.keys())
    member_information = get_members(members)

    merge_allocations(member_information, allocations)
    field_names.append("allocationStatus")
  
  # If 'event' isn't provided but a list of members is, return the listed members without any allocation information
  elif combinedEventId is None and len(members) > 0:
    member_information = get_members(members)

  # If 'event' is provided as well as a list of members, return the listed members with allocation information for that event
  elif combinedEventId is not None and len(members) > 0:
    member_information = get_members(members)
    allocations = get_allocations(combinedEventId)

    merge_allocations(member_information, allocations)
    field_names.append("allocationStatus")
  
  # Otherwise (no event, no list of members) return all members without any allocation information
  else:
    member_information = get_all_members()
  
  # Format fields
  for member in member_information:
    if member.get("lastUpdated"):
      member["lastUpdated"] = datetime.datetime.fromtimestamp(member["lastUpdated"]).isoformat()
    
    if member.get("telephone"):
      tel = phonenumbers.parse(member["telephone"], None)
      member["telephone"] = phonenumbers.format_number(tel, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    
    if member.get("emergencyContactTelephone"):
      tel = phonenumbers.parse(member["emergencyContactTelephone"], None)
      member["emergencyContactTelephone"] = phonenumbers.format_number(tel, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

  # Convert to CSV
  csv_string = StringIO()
  writer = csv.DictWriter(csv_string, fieldnames=field_names, extrasaction='ignore')
  writer.writeheader()
  writer.writerows(member_information)

  return {
    "statusCode": 200,
    "headers": headers,
    "body": csv_string.getvalue()
  }


def get_members(members):
  results = []

  for member in members:
    try:
      result = members_table.get_item(Key={
        "membershipNumber": member
      })['Item']

      results.append(result)
    except Exception as e:
      logger.error(f"Unable to get details of {member}: {str(e)}")

  return results


def get_all_members():
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = members_table.scan(
        ExclusiveStartKey=last_evaluated_key
      )
    else: 
      response = members_table.scan()

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return results


def get_allocations(combined_event_id):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = allocations_table.query(
        KeyConditionExpression=Key("combinedEventId").eq(combined_event_id),
        ExclusiveStartKey=last_evaluated_key,
        FilterExpression=Attr("allocation").ne("UNREGISTERED")
      )
    else: 
      response = allocations_table.query(
        KeyConditionExpression=Key("combinedEventId").eq(combined_event_id),
        FilterExpression=Attr("allocation").ne("UNREGISTERED")
      )

    last_evaluated_key = response.get('LastEvaluatedKey')    
    results.extend(response['Items'])
        
    if not last_evaluated_key:
      break

  return {allocation['membershipNumber'] : allocation['allocation'] for allocation in results}


def merge_allocations(member_information, allocations):
  for m in member_information:
    status = allocations.get(m['membershipNumber'], "NOT_REGISTERED")
    m['allocationStatus'] = status