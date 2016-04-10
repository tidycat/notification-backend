import logging
from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError
from botocore.exceptions import BotoCoreError
from boto3.dynamodb.conditions import Key
from notification_backend.http import format_response
from notification_backend.http import validate_jwt
from notification_backend.http import format_error_payload
from notification_backend.http import dynamodb_results


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
