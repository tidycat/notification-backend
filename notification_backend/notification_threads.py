import logging
import re
import requests
import dateutil.parser as dp
from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError
from botocore.exceptions import BotoCoreError
from boto3.dynamodb.conditions import Key
from notification_backend.http import format_response
from notification_backend.http import validate_jwt
from notification_backend.http import format_error_payload
from notification_backend.http import dynamodb_results
from notification_backend.http import dynamodb_new_item


logger = logging.getLogger("notification_backend")


class NotificationThreads(object):

    def __init__(self, lambda_event):
        for prop in ["payload",
                     "jwt_signing_secret",
                     "bearer_token",
                     "notification_dynamodb_endpoint_url",
                     "notification_user_notification_dynamodb_table_name"]:
            setattr(self, prop, lambda_event.get(prop))
            self.token = None
            self.userid = None
            resource_path = lambda_event.get('resource-path', "")
            self.thread_id_path = re.match('^/notification/threads/(.+)',
                                           resource_path)

    def process_thread_event(self, method_name):
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

    def find_thread(self):
        thread_id = self.thread_id_path.group(1)
        result = {}
        try:
            results = dynamodb_results(
                self.notification_dynamodb_endpoint_url,
                self.notification_user_notification_dynamodb_table_name,
                Key('user_id').eq(self.userid) & Key('thread_id').eq(int(thread_id))  # NOQA
            )
            # There should really only be one result
            result = results.next()
        except (Boto3Error, BotoCoreError, ClientError) as e:
            error_msg = "Error querying for thread %s from the datastore" % thread_id  # NOQA
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))
        except StopIteration:
            pass

        if not result:
            logger.debug("Could not find info for thread %s in the datastore" % thread_id)  # NOQA

            result = self.lookup_github_thread_info(thread_id)
            if not result:
                error_msg = "Could not find info for thread %s" % thread_id
                logger.info(error_msg)
                return format_response(404,
                                       format_error_payload(404, error_msg))

            result['tags'] = self.determine_list_of_tags(result)
            self.persist_thread_information(result)

        payload = {
            "data": {
                "type": "threads",
                "id": int(thread_id),
                "attributes": {
                    "thread_url": result.get('thread_url'),
                    "thread_subscription_url": result.get('thread_subscription_url'),  # NOQA
                    "reason": result.get('reason'),
                    "updated_at": int(result.get('updated_at')),
                    "subject_title": result.get('subject_title'),
                    "subject_url": result.get('subject_url'),
                    "subject_type": result.get('subject_type'),
                    "repository_owner": result.get('repository_owner'),
                    "repository_name": result.get('repository_name'),
                    "tags": result.get('tags')
                }
            }
        }
        return format_response(200, payload)

    def lookup_github_thread_info(self, thread_id):
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer %s" % self.token.get('github_token')
        }

        r = requests.get(
            'https://api.github.com/notifications/threads/%s' % thread_id,
            headers=headers
        )
        if not r.status_code == 200:
            logger.info("Could not find thread information for %s" % thread_id)
            logger.info("HTTP response code from GitHub: %s" % r.status_code)
            logger.debug("URL: %s" % r.url)
            logger.debug("Headers: %s" % r.headers)
            logger.debug("Response: %s" % r.text)
            return None
        try:
            thread_json = r.json()
        except ValueError as e:
            logger.error("Could not parse JSON from response %s. Error: %s" % (r.text, str(e)))  # NOQA
            return None

        update_at_epoch_time = dp.parse(thread_json.get('updated_at')).strftime('%s')  # NOQA
        return {
            "thread_id": int(thread_id),
            "thread_url": thread_json.get('url'),
            "thread_subscription_url": thread_json.get('subscription_url'),
            "reason": thread_json.get('reason'),
            "updated_at": int(update_at_epoch_time),
            "subject_title": thread_json.get('subject', {}).get('title'),
            "subject_url": thread_json.get('subject', {}).get('url'),
            "subject_type": thread_json.get('subject', {}).get('type'),
            "repository_owner": thread_json.get('repository', {}).get('owner', {}).get('login'),  # NOQA
            "repository_name": thread_json.get('repository', {}).get('name')
        }

    def determine_list_of_tags(self, result):
        # Set an appropriate tag name given the reason for the notification
        # event
        # https://developer.github.com/v3/activity/notifications/#notification-reasons
        reason_map = {
            "subscribed": "watching",
            "manual": "subscribed",
            "author": "owner",
            "comment": "commented",
            "mention": "mentioned",
            "team_mention": "mentioned",
            "assign": "assignee"
        }
        tag_list = []
        tag_list.append(reason_map.get(result.get('reason')))
        tag_list.append(result.get('subject_type').lower())
        tag_list.append(result.get('repository_owner').lower())
        tag_list.append(result.get('repository_name').lower())
        return tag_list

    def persist_thread_information(self, result):
        result['user_id'] = int(self.userid)
        try:
            dynamodb_new_item(
                self.notification_dynamodb_endpoint_url,
                self.notification_user_notification_dynamodb_table_name,
                result
            )
        except (Boto3Error, BotoCoreError) as e:
            error_msg = "Error writing info for thread %s to the datastore" % result.get('thread_id')  # NOQA
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))
