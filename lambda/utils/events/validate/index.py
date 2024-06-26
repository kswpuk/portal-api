import boto3
import datetime
import logging
import os
import re
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

EVENT_SERIES_TABLE_NAME = os.getenv('EVENT_SERIES_TABLE_NAME')
logger.info(f"EVENT_SERIES_TABLE_NAME = {EVENT_SERIES_TABLE_NAME}")

# Set up AWS
dynamodb = boto3.resource('dynamodb')

event_series_table = dynamodb.Table(EVENT_SERIES_TABLE_NAME)

def handler(event, context):
  logger.debug(event)

  eventSeriesId = str(event['eventSeriesId']).strip().lower()
  eventId = str(event['eventId']).strip().lower()

  validationErrors = []

  # Check that the event series exists
  logger.debug(f"Checking event series {eventSeriesId} exists")
  try:
    response = event_series_table.get_item(
      Key={
        "eventSeriesId": eventSeriesId
      },
      AttributesToGet=[
        "eventSeriesId"
      ]
    )
    if 'Item' not in response or 'eventSeriesId' not in response['Item']:
      validationErrors.append(f"Event series {eventSeriesId} does not exist")

  except Exception as e:
    logger.error(f"Unable to check event series {eventSeriesId} exists: {str(e)}")
    raise e

  # Do validation
  logger.debug(f"Validating input for {eventSeriesId}/{eventId}...")

  if len(eventId) > 20:
    validationErrors.append("Event ID cannot be longer than 20 characters")
  
  if len(eventId) < 2:
    validationErrors.append("Event ID must be at least 2 characters long")
  
  if not re.match("^[a-z0-9][-a-z0-9]+$", eventSeriesId):
    validationErrors.append("Event ID must start with a letter or a number, and can only contain lower case characters, numbers and hyphens")

  details = str(event.get("details", "")).strip()
  if details == "":
    validationErrors.append("Event details cannot be empty")
  
  location = str(event.get("location", "")).strip()
  if location == "":
    validationErrors.append("Location cannot be empty")

  locationType = str(event.get("locationType")).strip()
  if locationType not in ["physical", "virtual"]:
    validationErrors.append("Location type must be a supported value")
  
  if locationType == "physical":
    postcode = str(event.get("postcode")).strip()
    if postcode == "":
      validationErrors.append("Postcode must be provided for physical events")
  else:
    postcode = ""

  allowPastDates = event.get("_allowPastDates", False)
  
  if event.get("startDate") is None:
    validationErrors.append("Start date cannot be empty")
    startDate = None
  else:
    try:
      startDate = datetime.datetime.fromisoformat(event.get("startDate"))
    except Exception as e:
      validationErrors.append("Start date must be a valid date time")
      startDate = None
    
  if not allowPastDates and (startDate and datetime.datetime.now() > startDate):
    validationErrors.append("Start date can't be in the past")
  

  if event.get("endDate") is None:
    validationErrors.append("End date cannot be empty")
    endDate = None
  else:
    try:
      endDate = datetime.datetime.fromisoformat(event.get("endDate"))
    except Exception as e:
      validationErrors.append("End date must be a valid date time")
      endDate = None
    
  if not allowPastDates and (endDate and datetime.datetime.now() > endDate):
    validationErrors.append("End date can't be in the past")

  if startDate and endDate and startDate > endDate:
    validationErrors.append("Start date can't be after the end date")


  if event.get("registrationDate") is None:
    validationErrors.append("Registration date cannot be empty")
    registrationDate = None
  else:
    try:
      registrationDate = datetime.date.fromisoformat(event.get("registrationDate"))
    except Exception as e:
      validationErrors.append("Registration date must be a valid date")
      registrationDate = None
    
  if not allowPastDates and (registrationDate and datetime.date.today() > registrationDate):
    validationErrors.append("Registration date can't be in the past")
    
  if registrationDate and startDate and registrationDate > startDate.date():
    validationErrors.append("Registration date can't be after the start date")

  if event.get("eventUrl", "") == "":
    eventUrl = None
  else:
    try:
      result = urlparse(event.get("eventUrl"))
      if all([result.scheme, result.netloc]):
        eventUrl = event.get("eventUrl")
      else:
        raise
    except:
      validationErrors.append("Event URL is not valid")
  
  if event.get("cost", None) == None:
    cost = 0
  else:
    try:
      cost = float(event.get("cost"))

      if cost < 0:
        validationErrors.append("Event cost can not be negative")
    except:
      validationErrors.append("Event cost could not be parsed")
      cost = 0

  if event.get("payee", "") == "":
    payee = ""
  else:
    payee = str(event.get("payee")).strip()
  
  if event.get("attendanceCriteria") is None:
    attendanceCriteria = []
  elif isinstance(event.get("attendanceCriteria"), list):
    attendanceCriteria = []
    for a in event.get("attendanceCriteria"):
      if a not in ["active", "over25", "under25"]:
        validationErrors.append(f"Attendance criteria {a} not a supported value")
      else:
        attendanceCriteria.append(a)
  else:
    attendanceCriteria = None
    validationErrors.append("Attendance criteria must be a list")

  try:
    attendanceLimit = int(event.get("attendanceLimit", 0))

    if attendanceLimit < 0:
      validationErrors.append("Attendance limit cannot be less than 0")
  except:
    attendanceLimit = None
    validationErrors.append("Attendance limit must be numeric")
  
  allocationOnPayment = (event.get("allocationOnPayment", False) == True)

  if event.get("weightingCriteria") is None:
    weightingCriteria = {}
  elif isinstance(event.get("weightingCriteria"), dict):
    weightingCriteria = {}

    for k, v in event.get("weightingCriteria").items():
      if k not in ["under_25", "over_25", "attended", "attended_1yr", "attended_2yr", "attended_3yr", "attended_5yr", "droppedout_6mo", "droppedout_1yr", "droppedout_2yr", "droppedout_3yr", "noshow_6mo", "noshow_1yr", "noshow_2yr", "noshow_3yr", "joined_1yr", "joined_2yr", "joined_3yr", "joined_5yr", "qsa_1yr", "qsa_2yr", "qsa_3yr", "qsa_5yr"]:
        validationErrors.append(f"Weighting criteria {k} not a supported value")
        continue
      
      try:
        vi = int(v)

        if vi == 0:
          # Don't add criteria that are 0
          continue
        
        weightingCriteria[k] = vi
      except:
        validationErrors.append(f"Weighting criteria value {v} for {k} must be numeric")

  else:
    weightingCriteria = None
    validationErrors.append("Attendance criteria must be an object")

  if len(validationErrors) > 0:
    return {
      "valid": False,
      "errors": validationErrors
    }
  else:
    return {
      "valid": True,
      "errors": [],
      "event": {
        "eventSeriesId": eventSeriesId,
        "eventId": eventId,
        "details": details,
        "location": location,
        "postcode": postcode,
        "locationType": locationType,
        "registrationDate": registrationDate.isoformat(),
        "startDate": startDate.isoformat(),
        "endDate": endDate.isoformat(),
        "eventUrl": eventUrl,
        "cost": cost,
        "payee": payee,
        "attendanceCriteria": attendanceCriteria,
        "attendanceLimit": attendanceLimit,
        "allocationOnPayment": allocationOnPayment,
        "weightingCriteria": weightingCriteria
      }
    }