import os
import boto3
import json
import time
import urllib.request
import jwt
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# envs
TABLE_NAME = os.environ['TABLE_NAME']
AWS_REGION = os.environ['AWS_REGION']
COGNITO_USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
COGNITO_APP_CLIENT_ID = os.environ['COGNITO_APP_CLIENT_ID']

logger.debug(f"AWS Region: "+AWS_REGION)
logger.debug(f"Table Name: "+TABLE_NAME)
logger.debug(f"Cognito User Pool: "+COGNITO_USER_POOL_ID)
logger.debug(f"Cognito App Client: "+COGNITO_APP_CLIENT_ID)


keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(AWS_REGION, COGNITO_USER_POOL_ID)
logger.info(f"Downloading Cognito key from {keys_url}")

# instead of re-downloading the public keys every time
# we download them only on cold start
# https://aws.amazon.com/blogs/compute/container-reuse-in-lambda/
with urllib.request.urlopen(keys_url) as f:
    response = f.read()
keys = json.loads(response.decode('utf-8'))['keys']

logger.info("Downloaded Cognito key")

def handler(event, context):
    logger.debug(event)

    logger.info("Parsing token")
    token_data = parse_token_data(event)
    if token_data['valid'] is False:
        logger.warning("Token not in correct format")
        return get_deny_policy()

    logger.info("Token parsed successfully; validating and retrieving claims")
    try:
        claims = validate_token(token_data['token'])
        if claims is False:
            return get_deny_policy()

        groups = claims['cognito:groups']
        logger.debug(f"Groups: {groups}")

        results = batch_query_wrapper(TABLE_NAME, 'group', groups)
        logger.debug(f"Query results: {results}")

        if len(results) > 0:
            policy = {
                'Version': "2012-10-17",
                'Statement': []
            }
            for item in results:
                pol = json.loads(item['policy'].replace('{membershipNumber}', claims['username']))
                policy['Statement'] = policy['Statement'] + pol['Statement']
            
            logger.debug(f"Policy generated: {policy}")

            return get_response_object(policy, principalId=claims['username'], context={"membershipNumber": claims['username'], "groups": ','.join(groups)})

        logger.warning("No matching policies found in DynamoDB")
        return get_deny_policy()

    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        raise e

    return get_deny_policy()


def get_response_object(policyDocument, principalId='unknown', context={}):
    return {
        "principalId": principalId,
        "policyDocument": policyDocument,
        "context": context,
        "usageIdentifierKey": "{api-key}"
    }


def get_deny_policy():
    return {
        "principalId": "unknown",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Deny",
                    "Resource": "arn:aws:execute-api:*:*:*/ANY/*"
                }
            ]
        },
        "context": {},
        "usageIdentifierKey": "{api-key}"
    }


def batch_query_wrapper(table, key, values):
    results = []

    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    values_list = [values[x:x + 25] for x in range(0, len(values), 25)]

    for vlist in values_list:
        response = dynamodb.batch_get_item(RequestItems={table: {'Keys': [{key: val} for val in vlist]}})
        results.extend(response['Responses'][table])

        while response['UnprocessedKeys']:
            response = dynamodb.batch_get_item(RequestItems={table: {'Keys': [{key: val} for val in vlist]}})
            results.extend(response['Response'][table])

    return results


def parse_token_data(event):
    response = {'valid': False}

    if 'authorizationToken' not in event:
        return response

    auth_header = event['authorizationToken']
    auth_header_list = auth_header.split(' ')

    # deny request of header isn't made out of two strings, or
    # first string isn't equal to "Bearer" (enforcing following standards,
    # but technically could be anything or could be left out completely)
    if len(auth_header_list) != 2 or auth_header_list[0] != 'Bearer':
        return response

    access_token = auth_header_list[1]
    return {
        'valid': True,
        'token': access_token
    }


def validate_token(token):
    try:
        # get the kid from the headers prior to verification
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
    except jwt.PyJWTError as e:
        logger.warning(f'Failed to decode token header: {e}')
        return False

    # search for the kid in the downloaded public keys
    key_dict = None
    for k in keys:
        if kid == k.get('kid'):
            key_dict = k
            break

    if key_dict is None:
        logger.warning('Public key not found in jwks.json')
        return False

    try:
        # construct the public key using PyJWT
        public_key = jwt.PyJWK.from_dict(key_dict).key

        # decode and verify the token signature, algorithm, and expiration
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        logger.info('Signature successfully verified')
    except jwt.ExpiredSignatureError:
        logger.warning('Token is expired')
        return False
    except jwt.PyJWTError as e:
        logger.warning(f'Signature or token verification failed: {e}')
        return False

    # and the Audience (use claims['client_id'] if verifying an access token)
    token_client_id = claims.get('client_id') or claims.get('aud')
    if token_client_id != COGNITO_APP_CLIENT_ID:
        logger.warning('Token was not issued for this audience')
        return False

    # now we can use the claims
    return claims