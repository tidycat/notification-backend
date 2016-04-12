import logging
import re
from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError
from botocore.exceptions import BotoCoreError
from boto3.dynamodb.conditions import Key, Attr
from notification_backend.http import format_response
from notification_backend.http import validate_jwt
from notification_backend.http import format_error_payload
from notification_backend.http import dynamodb_results
from notification_backend.http import dynamodb_new_item
from notification_backend.http import dynamodb_delete_item
from notification_backend.http import dynamodb_get_item


logger = logging.getLogger("notification_backend")


class NotificationTags(object):

    def __init__(self, lambda_event):
        for prop in ["payload",
                     "jwt_signing_secret",
                     "bearer_token",
                     "notification_dynamodb_endpoint_url",
                     "notification_tags_dynamodb_table_name"]:
            setattr(self, prop, lambda_event.get(prop))
            self.token = None
            self.userid = None
            resource_path = lambda_event.get('resource-path', "")
            self.tag_name_path = re.match('^/notification/tags/(.+)',
                                          resource_path)

    def process_tag_event(self, method_name):
        self.token = validate_jwt(self.bearer_token, self.jwt_signing_secret)
        if not self.token:
            error_msg = "Invalid JSON Web Token"
            logger.info(error_msg)
            return format_response(401, format_error_payload(401, error_msg))

        self.userid = self.token.get('sub')
        if not self.userid:
            error_msg = "sub field not present in JWT"
            logger.info(error_msg)
            return format_response(401, format_error_payload(401, error_msg))

        method_to_call = getattr(self, method_name)
        return method_to_call()

    def find_all_tags(self):
        tag_list = []
        try:
            results = dynamodb_results(
                self.notification_dynamodb_endpoint_url,
                self.notification_tags_dynamodb_table_name,
                Key('user_id').eq(self.userid)
            )
            for result in results:
                res = {
                    "id": result.get('tag_name'),
                    "type": "tags",
                    "attributes": {
                        "color": result.get('tag_color')
                    }
                }
                tag_list.append(res)
        except (Boto3Error, BotoCoreError, ClientError) as e:
            error_msg = "Error querying the datastore"
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))

        payload = {
            "data": tag_list
        }
        return format_response(200, payload)

    def create_new_tag(self):
        post_payload = self.payload.get('data')

        # The POST payload needs to have the 'type' member
        post_type = post_payload.get('type')
        if post_type != "tags":
            error_msg = "Payload missing 'type' member"
            logger.info(error_msg)
            return format_response(400, format_error_payload(400, error_msg))

        # The POST payload needs to have the 'id' member
        tag_id = post_payload.get('id')
        if not tag_id:
            error_msg = "Payload missing 'id' member"
            logger.info(error_msg)
            return format_response(400, format_error_payload(400, error_msg))

        # If no color is specified, default it to #ffffff
        tag_color = post_payload.get('attributes', {}).get('color', '#ffffff')

        # Create the specified tag, if it doesn't already exist
        try:
            item = {
                "user_id": self.userid,
                "tag_name": tag_id,
                "tag_color": tag_color
            }
            dynamodb_new_item(
                self.notification_dynamodb_endpoint_url,
                self.notification_tags_dynamodb_table_name,
                item,
                Attr("user_id").ne(self.userid) & Attr("tag_name").ne(tag_id)
            )
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":  # NOQA
                error_msg = "Tag %s already exists" % tag_id
                logger.info(error_msg)
                return format_response(409,
                                       format_error_payload(409, error_msg))
            error_msg = "Error querying the datastore"
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))
        except (Boto3Error, BotoCoreError) as e:
            error_msg = "Error querying the datastore"
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))

        payload = {
            "data": {
                "type": "tags",
                "id": tag_id,
                "attributes": {
                    "color": tag_color
                }
            }
        }
        return format_response(201, payload)

    def delete_tag(self):
        tag_name = self.tag_name_path.group(1)
        key = {
            "user_id": self.userid,
            "tag_name": tag_name
        }
        try:
            dynamodb_delete_item(
                self.notification_dynamodb_endpoint_url,
                self.notification_tags_dynamodb_table_name,
                key,
                Attr("user_id").eq(self.userid) & Attr("tag_name").eq(tag_name)
            )
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":  # NOQA
                error_msg = "Tag %s does not exist" % tag_name
                logger.info(error_msg)
                return format_response(409,
                                       format_error_payload(409, error_msg))
            error_msg = "Error deleting tag %s from the datastore" % tag_name
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))
        except (Boto3Error, BotoCoreError) as e:
            error_msg = "Error deleting tag %s from the datastore" % tag_name
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))

        payload = {
            "meta": {
                "message": "Tag %s successfully deleted" % tag_name
            }
        }
        return format_response(200, payload)

    def find_tag(self):
        tag_name = self.tag_name_path.group(1)
        key = {
            "user_id": self.userid,
            "tag_name": tag_name
        }
        result = {}
        try:
            result = dynamodb_get_item(
                self.notification_dynamodb_endpoint_url,
                self.notification_tags_dynamodb_table_name,
                key
            )
        except (Boto3Error, BotoCoreError, ClientError) as e:
            error_msg = "Error getting tag %s from the datastore" % tag_name
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))

        if not result:
            error_msg = "Could not find information for tag %s" % tag_name
            logger.info(error_msg)
            return format_response(404, format_error_payload(404, error_msg))

        payload = {
            "data": {
                "type": "tags",
                "id": tag_name,
                "attributes": {
                    "color": result.get('tag_color')
                }
            }
        }
        return format_response(200, payload)
