import json
import jwt
import boto3
import logging
import requests


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
    logger.debug("Response: %s" % response)
    if http_status_code == 200:
        return response
    raise TypeError(json.dumps(response))


def validate_jwt(token, secret):
    try:
        return jwt.decode(token, secret)
    except jwt.exceptions.InvalidTokenError as e:
        logger.debug("Invalid Token Error: %s" % str(e))
        return None


def dynamodb_results(endpoint_url, table_name, key, index_name=None):
    exclusive_start_key = None
    more_results = True
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)
    while more_results:
        kwargs = {"KeyConditionExpression": key}
        if index_name:
            kwargs.update({"IndexName": index_name})
        if exclusive_start_key:
            kwargs.update({"ExclusiveStartKey": exclusive_start_key})
        results = table.query(**kwargs)
        for item in results['Items']:
            yield item
        more_results = 'LastEvaluatedKey' in results
        exclusive_start_key = results.get('LastEvaluatedKey')


def dynamodb_new_item(endpoint_url,
                      table_name,
                      item,
                      condition_expression=None):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)
    kwargs = {"Item": item}
    if condition_expression:
        kwargs.update({"ConditionExpression": condition_expression})
    table.put_item(**kwargs)


def dynamodb_delete_item(endpoint_url,
                         table_name,
                         key,
                         condition_expression):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)
    table.delete_item(Key=key, ConditionExpression=condition_expression)


def dynamodb_update_item(endpoint_url,
                         table_name,
                         key,
                         update_expression,
                         expr_attribute_values,
                         condition_expression=None):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)
    kwargs = {}
    kwargs.update({"Key": key})
    kwargs.update({"UpdateExpression": update_expression})
    kwargs.update({"ExpressionAttributeValues": expr_attribute_values})
    kwargs.update({"ReturnValues": "UPDATED_NEW"})
    if condition_expression:
        kwargs.update({"ConditionExpression": condition_expression})
    result = table.update_item(**kwargs)
    return result


def get_notification_threads(gh_bearer_token, from_date):
    more_results = True
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer %s" % gh_bearer_token
    }
    url = 'https://api.github.com/notifications?all=true&since=%s' % from_date
    while more_results:
        r = requests.get(url, headers=headers)
        if not r.status_code == 200:
            logger.error("Could not fetch notifications")
            logger.error("HTTP response code from GitHub: %s" % r.status_code)
            logger.error("URL: %s" % r.url)
            logger.error("Headers: %s" % r.headers)
            logger.error("Response: %s" % r.text)
            raise StopIteration
        try:
            thread_json = r.json()
        except ValueError as e:
            logger.error("Could not parse JSON from response %s. Error: %s" % (r.text, str(e)))  # NOQA
            raise StopIteration

        for result in thread_json:
            yield result

        more_results = False
        if 'next' in r.links:
            more_results = True
            url = r.links['next'].get('url')


def send_sns_message(event, context, topic_arn):  # pragma: no cover
    logger.info("Publishing SNS message for endpoint: %s" % event.get('resource-path'))  # NOQA
    client = boto3.client('sns')
    response = client.publish(TopicArn=topic_arn, Message=json.dumps(event))
    logger.debug("SNS publish result: %s" % response)


def is_sns_event(event):
    """
    Determine if the event we just received is an SNS event
    """
    if "Records" in event:
        return True
    return False
