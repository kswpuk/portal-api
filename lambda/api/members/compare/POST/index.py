
import boto3
import json
import logging
import os

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
  # Get submitted list
  body = json.loads(event['body'])
  compass_members = body.get('members', [])

  if len(compass_members) == 0:
    logger.warn("Empty member list received")
    return {
      "statusCode": 400,
      "headers": headers,
      "body": "Member list can not be empty"
    }

  # Get list from Portal
  try:
    portal_members = scan_members()
  except Exception as e:
    logger.error(f"Unable to list members: {str(e)}")
    return {
      "statusCode": 500,
      "headers": headers,
      "body": "Unable to list members"
    }

  # Combine and restructure lists
  combined_members = set(compass_members)
  portal_members_map = {}
  for m in portal_members:
    portal_members_map[int(m["membershipNumber"])] = m
    combined_members.add(int(m["membershipNumber"]))

  # Calculate response
  comparison_result = []
  for m in combined_members:
    compass = (m in compass_members)
    portal = (m in portal_members_map)
    
    name = None

    if portal:
      pm = portal_members_map[m]
      fname = pm.get('preferredName', pm['firstName'])
      if fname.strip() == "":
        fname = pm['firstName']

      name = fname + " " + pm['surname']

      portal_active = (portal_members_map[m]['status'] == "ACTIVE")
      
      if portal_active == compass:
        action = "NONE"
      elif portal_active and not compass:
        action = "ADD_TO_COMPASS"
      elif not portal_active:
        action = "REMOVE_FROM_COMPASS"
    else:
      action = "REMOVE_FROM_COMPASS"
    
    comparison_result.append({
      "membershipNumber": m,
      "name": name,
      "action": action
    })

  return {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(comparison_result)
  }

def scan_members(**kwargs):
  results = []
  last_evaluated_key = None

  while True:
    if last_evaluated_key:
      response = members_table.scan(
        ExclusiveStartKey=last_evaluated_key,
        ProjectionExpression="membershipNumber,firstName,preferredName,surname,#s",
        ExpressionAttributeNames={
          "#s": "status"
        },
        **kwargs
      )
    else: 
      response = members_table.scan(
        ProjectionExpression="membershipNumber,firstName,preferredName,surname,#s",
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
