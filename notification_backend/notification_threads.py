import logging
import re
import requests
import urlparse
from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError
from botocore.exceptions import BotoCoreError
from boto3.dynamodb.conditions import Key, Attr
from notification_backend.http import format_response
from notification_backend.http import validate_jwt
from notification_backend.http import format_error_payload
from notification_backend.http import dynamodb_results
from notification_backend.http import dynamodb_new_item
from notification_backend.http import dynamodb_update_item
from notification_backend.http import dynamodb_delete_item
from notification_backend.time import get_epoch_time
from notification_backend.time import get_current_epoch_time


logger = logging.getLogger("notification_backend")
BACKLOG_TIME_LIMIT = 2592000 * 6  # 6 months, in seconds
DEFAULT_BACKLOG_SEARCH_TIME = 604800  # 1 week, in seconds


class NotificationThreads(object):

    def __init__(self, lambda_event):
        for prop in ["payload",
                     "jwt_signing_secret",
                     "bearer_token",
                     "notification_dynamodb_endpoint_url",
                     "notification_user_notification_dynamodb_table_name",
                     "notification_user_notification_date_dynamodb_index_name"]:  # NOQA
            setattr(self, prop, lambda_event.get(prop))
            self.token = None
            self.userid = None
            self.resource_path = lambda_event.get('resource-path', "")
            self.thread_id_path = re.match('^/notification/threads/(.+)',
                                           self.resource_path)

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

        updated_at = get_epoch_time(thread_json.get('updated_at'))
        return {
            "thread_id": int(thread_id),
            "thread_url": thread_json.get('url'),
            "thread_subscription_url": thread_json.get('subscription_url'),
            "reason": thread_json.get('reason'),
            "updated_at": updated_at,
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

    def find_all_threads(self):
        current_epoch_time = get_current_epoch_time()
        params = urlparse.parse_qs(urlparse.urlparse(self.resource_path).query)
        self.from_date = params.get('from')
        if self.from_date:
            # urlparse.parse_qs returns a list of values corresponding to the
            # specified key, we only effectively care about the first value
            self.from_date = self.from_date[0]
        else:
            self.from_date = current_epoch_time - DEFAULT_BACKLOG_SEARCH_TIME

        try:
            self.from_date = int(self.from_date)
        except ValueError as e:
            error_msg = "'from' parameter needs to be in epoch seconds, %s is not valid" % self.from_date  # NOQA
            logger.info("%s: %s" % (error_msg, str(e)))
            return format_response(400, format_error_payload(400, error_msg))

        if self.from_date <= (current_epoch_time - BACKLOG_TIME_LIMIT):
            self.from_date = current_epoch_time - BACKLOG_TIME_LIMIT

        thread_list = []
        try:
            results = dynamodb_results(
                self.notification_dynamodb_endpoint_url,
                self.notification_user_notification_dynamodb_table_name,
                Key('user_id').eq(self.userid) & Key('updated_at').gte(self.from_date),  # NOQA
                self.notification_user_notification_date_dynamodb_index_name
            )
            for result in results:
                res = {
                    "type": "threads",
                    "id": int(result.get('thread_id')),
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
                thread_list.append(res)
        except (Boto3Error, BotoCoreError, ClientError) as e:
            error_msg = "Error querying the datastore"
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))

        payload = {
            "data": thread_list
        }
        return format_response(200, payload)

    def update_thread(self):
        thread_id = int(self.thread_id_path.group(1))
        patch_payload = self.payload.get('data', {})

        # The PATCH payload needs to have the 'type' member
        patch_type = patch_payload.get('type')
        if patch_type != "threads":
            error_msg = "Invalid 'type' member, should be 'threads'"
            logger.info(error_msg)
            return format_response(400, format_error_payload(400, error_msg))

        # The PATCH payload needs to have the 'id' member
        m_thread_id = patch_payload.get('id')
        if m_thread_id != thread_id:
            error_msg = "Invalid 'id' member, should match patch url"
            logger.info(error_msg)
            return format_response(400, format_error_payload(400, error_msg))

        # Gather the attributes that need to be updated
        updated_at = patch_payload.get('attributes', {}).get('updated_at')
        subject_title = patch_payload.get('attributes', {}).get('subject_title')  # NOQA
        reason = patch_payload.get('attributes', {}).get('reason')
        tags = patch_payload.get('attributes', {}).get('tags', [])

        # The understanding here is that any attribute that isn't explicitly
        # specified is essentially blanked out (with a falsey value)
        key = {
            "user_id": self.userid,
            "thread_id": thread_id
        }
        values = {
            ":u": updated_at,
            ":s": subject_title,
            ":r": reason,
            ":t": tags
        }
        update_expression = "set updated_at=:u, subject_title=:s, reason=:r, tags=:t"  # NOQA
        try:
            dynamodb_update_item(
                endpoint_url=self.notification_dynamodb_endpoint_url,
                table_name=self.notification_user_notification_dynamodb_table_name,  # NOQA
                key=key,
                update_expression=update_expression,
                expr_attribute_values=values
            )
        except (Boto3Error, BotoCoreError, ClientError) as e:
            error_msg = "Error updating thread %s in the datastore" % thread_id
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))

        payload = {
            "meta": {
                "message": "Thread %s updated successfully" % thread_id
            }
        }
        return format_response(200, payload)

    def delete_thread(self):
        thread_id = int(self.thread_id_path.group(1))
        key = {
            "user_id": self.userid,
            "thread_id": thread_id
        }
        try:
            dynamodb_delete_item(
                endpoint_url=self.notification_dynamodb_endpoint_url,
                table_name=self.notification_user_notification_dynamodb_table_name,  # NOQA
                key=key,
                condition_expression=Attr("user_id").eq(self.userid) & Attr("thread_id").eq(thread_id)  # NOQA
            )
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":  # NOQA
                error_msg = "Thread %s does not exist" % thread_id
                logger.info(error_msg)
                return format_response(409,
                                       format_error_payload(409, error_msg))
            error_msg = "Error deleting thread %s from the datastore" % thread_id  # NOQA
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))
        except (Boto3Error, BotoCoreError) as e:
            error_msg = "Error deleting thread %s from the datastore" % thread_id  # NOQA
            logger.error("%s: %s" % (error_msg, str(e)))
            return format_response(500, format_error_payload(500, error_msg))

        payload = {
            "meta": {
                "message": "Thread %s successfully deleted" % thread_id
            }
        }
        return format_response(200, payload)
