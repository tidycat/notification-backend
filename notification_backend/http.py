import json
import jwt
import boto3
import logging


logger = logging.getLogger("notification_backend")


def format_error_payload(http_status_code, message):
    return {
        "errors": [
            {
                "status": http_status_code,
                "detail": message
            }
        ]
    }


def format_response(http_status_code, payload):
    response = {
        "http_status": http_status_code,
        "data": payload
    }
    if http_status_code == 200:
        return response
    raise TypeError(json.dumps(response))


def validate_jwt(token, secret):
    try:
        return jwt.decode(token, secret)
    except jwt.exceptions.InvalidTokenError as e:
        logger.debug("Invalid Token Error: %s" % str(e))
        return None


def dynamodb_results(endpoint_url, table_name, key):
    exclusive_start_key = None
    more_results = True
    while more_results:
        dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
        table = dynamodb.Table(table_name)
        kwargs = {"KeyConditionExpression": key}
        if exclusive_start_key:
            kwargs.append({"ExclusiveStartKey": exclusive_start_key})
        results = table.query(**kwargs)
        for item in results['Items']:
            yield item
        more_results = 'LastEvaluatedKey' in results
        exclusive_start_key = results.get('LastEvaluatedKey')
