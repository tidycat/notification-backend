import unittest
from mock import patch
from mock import call
import responses
from notification_backend.notification_threads import NotificationThreads
import json
import jwt
import re


class TestBackfillNotifications(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_threads.dynamodb_results')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_results = patcher1.start()

        patcher2 = patch('notification_backend.notification_threads.send_sns_message')  # NOQA
        self.addCleanup(patcher2.stop)
        self.mock_send_sns_msg = patcher2.start()

        self.jwt_signing_secret = "shhsekret"
        self.token = jwt.encode({"sub": "333333"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event = {
            "jwt_signing_secret": self.jwt_signing_secret,
            "bearer_token": self.token,
            "payload": {},
            "resource-path": "/notification/backfill",
            "notification_dynamodb_endpoint_url": "http://example.com",
            "notification_user_notification_dynamodb_table_name": "fakethreads",  # NOQA
            "notification_sns_arn": "fakesnsarn"
        }

    def test_backfill_notifications(self):
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError):
            t.process_thread_event("backfill_notifications")
        self.lambda_event['resource-path'] = "/notification/backfill_async_trigger"  # NOQA
        expected_calls = [call(self.lambda_event, {}, "fakesnsarn")]
        self.assertEqual(self.mock_send_sns_msg.mock_calls, expected_calls)

    @responses.activate
    def test_github_api_400(self):
        url_re = re.compile(r'https://api.github.com/notifications\?all=true&since=.*')  # NOQA
        responses.add(**{
            'method': responses.GET,
            'url': url_re,
            'body': '{"error": "message"}',
            'status': 400
        })
        t = NotificationThreads(self.lambda_event)
        t.process_thread_event("backfill_notifications_asynchronously")
        self.assertEqual(self.mock_send_sns_msg.mock_calls, [])

    @responses.activate
    def test_github_api_invalid_json(self):
        url_re = re.compile(r'https://api.github.com/notifications\?all=true&since=.*')  # NOQA
        responses.add(**{
            'method': responses.GET,
            'url': url_re,
            'body': 'fake json',
            'status': 200
        })
        t = NotificationThreads(self.lambda_event)
        t.process_thread_event("backfill_notifications_asynchronously")
        self.assertEqual(self.mock_send_sns_msg.mock_calls, [])

    @responses.activate
    def test_single_notification_result(self):
        url_re = re.compile(r'https://api.github.com/notifications\?all=true&since=.*')  # NOQA
        output = [
            {"id": "00001"}
        ]
        responses.add(**{
            'method': responses.GET,
            'url': url_re,
            'body': json.dumps(output),
            'status': 200
        })
        t = NotificationThreads(self.lambda_event)
        t.process_thread_event("backfill_notifications_asynchronously")

        event_0 = self.lambda_event
        event_0['resource-path'] = "/notification/threads/00001"
        event_0['http-method'] = "/notification/threads/00001"
        expected_call_0 = call(event_0, {}, "fakesnsarn")
        self.assertTrue(expected_call_0 in self.mock_send_sns_msg.mock_calls)
        self.assertEqual(len(self.mock_send_sns_msg.mock_calls), 1)

    @responses.activate
    def test_multiple_notification_results(self):

        def request_callback(request):
            output = [
                {"id": "00001"}
            ]
            headers = {'link': '<https://api.github.com/notificationsall=true&page=2&since=yesterday>; rel="next", <https://api.github.com/notificationsall=true&page=9&since=yesterday>; rel="last"'}  # NOQA
            return (200, headers, json.dumps(output))

        url_re = re.compile(r'https://api.github.com/notifications\?all=true&since=.*')  # NOQA
        responses.add_callback(responses.GET, url_re, callback=request_callback)  # NOQA

        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.github.com/notificationsall=true&page=2&since=yesterday',  # NOQA
            'body': json.dumps([{"id": "00002"}]),
            'status': 200
        })

        t = NotificationThreads(self.lambda_event)
        t.process_thread_event("backfill_notifications_asynchronously")

        event_0 = self.lambda_event
        event_0['resource-path'] = "/notification/threads/00001"
        event_0['http-method'] = "/notification/threads/00001"
        expected_call_0 = call(event_0, {}, "fakesnsarn")
        self.assertTrue(expected_call_0 in self.mock_send_sns_msg.mock_calls)

        event_1 = self.lambda_event
        event_1['resource-path'] = "/notification/threads/00002"
        event_1['http-method'] = "/notification/threads/00002"
        expected_call_1 = call(event_1, {}, "fakesnsarn")
        self.assertTrue(expected_call_1 in self.mock_send_sns_msg.mock_calls)

        self.assertEqual(len(self.mock_send_sns_msg.mock_calls), 2)
