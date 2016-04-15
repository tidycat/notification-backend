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


def dynamodb_get_item(endpoint_url,
                      table_name,
                      key):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)
    result = table.get_item(Key=key)

    if 'Item' in result:
        return result['Item']
    return None


def dynamodb_update_item(endpoint_url,
                         table_name,
                         key,
                         update_expression,
                         expr_attribute_values,
                         condition_expression):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)
    result = table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expr_attribute_values,
        ConditionExpression=condition_expression,
        ReturnValues="UPDATED_NEW"
    )
    return result
