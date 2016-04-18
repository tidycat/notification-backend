import unittest
from mock import patch
from notification_backend.notification_threads import NotificationThreads
import json
import jwt
from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError


class TestDeleteThread(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_threads.dynamodb_delete_item')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_delete = patcher1.start()

        self.jwt_signing_secret = "shhsekret"
        self.token = jwt.encode({"sub": "1234"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event = {
            "jwt_signing_secret": self.jwt_signing_secret,
            "bearer_token": self.token,
            "resource-path": "/notification/threads/123456",
            "payload": {
                "data": {
                    "id": 123456,
                    "type": "threads",
                    "attributes": {
                        "thread_url": "http://example.com/threadurl",
                        "thread_subscription_url": "http://example.com/threadsubscriptionurl",  # NOQA
                        "reason": "subscribed",
                        "updated_at": 3332333,
                        "subject_title": "This is a title",
                        "subject_url": "http://example.com/subjecturl",
                        "subject_type": "PullRequest",
                        "repository_owner": "octocat",
                        "repository_name": "octorepo",
                        "tags": [
                            "tag1",
                            "tag2"
                        ]
                    }
                }
            },
            "notification_dynamodb_endpoint_url": "http://example.com",
            "notification_user_notification_dynamodb_table_name": "faketable",
            "notification_user_notification_date_dynamodb_index_name": "fakendex"  # NOQA
        }

    def test_thread_does_not_exist(self):
        ce = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "OperationName")  # NOQA
        self.mock_db_delete.side_effect = ce
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("delete_thread")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 409)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            409
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Thread 123456 does not exist"
        )
        self.assertTrue(self.mock_db_delete.mock_calls > 0)

    def test_error_querying_datastore_clienterror(self):
        ce = ClientError({"Error": {"Code": "random"}}, "OperationName")  # NOQA
        self.mock_db_delete.side_effect = ce
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("delete_thread")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error deleting thread 123456 from the datastore"
        )
        self.assertTrue(self.mock_db_delete.mock_calls > 0)

    def test_error_querying_datastore_boto3error(self):
        self.mock_db_delete.side_effect = Boto3Error
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("delete_thread")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error deleting thread 123456 from the datastore"
        )
        self.assertTrue(self.mock_db_delete.mock_calls > 0)

    def test_delete_thread(self):
        t = NotificationThreads(self.lambda_event)
        result_json = t.process_thread_event("delete_thread")
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('meta').get('message'),
                         'Thread 123456 successfully deleted')
        self.assertTrue(self.mock_db_delete.mock_calls > 0)
