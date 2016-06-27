import unittest
import json
import jwt
import time
from datetime import datetime
from mock import patch
from boto3.exceptions import Boto3Error
from notification_backend.notification_threads import NotificationThreads


class TestFindAllThreads(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_threads.dynamodb_results')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_results = patcher1.start()

        patcher2 = patch('notification_backend.notification_threads.get_current_epoch_time')  # NOQA
        self.addCleanup(patcher2.stop)
        self.mock_time = patcher2.start()
        self.mock_time.return_value = time.mktime(datetime(2016, 1, 10).timetuple())  # NOQA

        self.jwt_signing_secret = "shhsekret"
        self.token = jwt.encode({"sub": "333333"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event = {
            "jwt_signing_secret": self.jwt_signing_secret,
            "bearer_token": self.token,
            "payload": {},
            "resource-path": "/notification/threads",
            "notification_dynamodb_endpoint_url": "http://example.com",
            "notification_user_notification_dynamodb_table_name": "fakethreads"
        }

        self.backlog_time_limit = 2592000 * 6  # 6 months, in seconds
        self.default_backlog_search_time = 604800  # 1 week, in seconds

        self.mock_db_results.return_value = [{
            "thread_id": 12345678,
            "thread_url": "http://api.example.com/fake/12345678",
            "thread_subscription_url": "http://api.example.com/fake/12345678/subscribe",  # NOQA
            "reason": "subscribed",
            "updated_at": 1460443217,
            "subject_title": "Fake Issue",
            "subject_url": "http://example.com/fake/12345678",
            "subject_type": "Issue",
            "repository_owner": "octocat",
            "repository_name": "left-pad"
        }]

    def test_invalid_from_date(self):
        self.lambda_event['resource-path'] = "/notification/threads?from=faketest"  # NOQA
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_all_threads")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 400)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            400
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "'from' parameter needs to be in epoch seconds, faketest is not valid"  # NOQA
        )

    def test_default_from_date(self):
        expected_from_date = self.mock_time.return_value - self.default_backlog_search_time  # NOQA
        t = NotificationThreads(self.lambda_event)
        result_json = t.process_thread_event("find_all_threads")
        self.assertEqual(t.from_date, expected_from_date)
        result_attrs = result_json.get('data').get('data')[0].get('attributes')
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('data')[0].get('type'), "threads")  # NOQA
        self.assertEqual(result_json.get('data').get('data')[0].get('id'), 12345678)  # NOQA
        self.assertEqual(result_attrs.get('thread_url'), "http://api.example.com/fake/12345678")  # NOQA
        self.assertEqual(result_attrs.get('thread_subscription_url'), "http://api.example.com/fake/12345678/subscribe")  # NOQA
        self.assertEqual(result_attrs.get('reason'), "subscribed")
        self.assertEqual(result_attrs.get('updated_at'), 1460443217)
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    def test_out_of_range_form_date(self):
        self.lambda_event['resource-path'] = "/notification/threads?from=0"
        expected_from_date = self.mock_time.return_value - self.backlog_time_limit  # NOQA
        t = NotificationThreads(self.lambda_event)
        t.process_thread_event("find_all_threads")
        self.assertEqual(t.from_date, expected_from_date)
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    def test_dynamodb_error(self):
        self.mock_db_results.side_effect = Boto3Error
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_all_threads")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error querying the datastore"
        )
