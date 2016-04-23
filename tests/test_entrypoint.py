import unittest
import logging
from mock import patch
from mock import call
from notification_backend.entrypoint import handler
import json


class TestEntrypoint(unittest.TestCase):

    def setUp(self):
        patcher2 = patch('notification_backend.entrypoint.NotificationThreads')
        self.addCleanup(patcher2.stop)
        self.mock_notif_threads = patcher2.start()

    def test_log_level_warning(self):
        logger = logging.getLogger("notification_backend")
        self.assertTrue(logger.getEffectiveLevel() >= logging.INFO,
                        "Log level needs to be set to INFO or better")

    def test_invalid_path(self):
        with self.assertRaises(TypeError) as cm:
            handler({"resource-path": "/"}, {})
        result_json = json.loads(str(cm.exception))
        data_result = result_json.get('data')
        self.assertEqual(result_json.get('http_status'), 400)
        self.assertEqual(data_result.get('errors')[0].get('detail'),
                         "Invalid path /")
        self.assertEqual(data_result.get('errors')[0].get('status'), 400)
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 0)

    def test_ping_endpoint(self):
        event = {
            "resource-path": "/notification/ping",
            "http-method": "GET"
        }
        result = handler(event, {})
        self.assertEqual(result.get('http_status'), 200)
        self.assertTrue("version" in result.get('data').get('meta'))
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 0)

    def test_find_thread_endpoint(self):
        event = {
            "resource-path": "/notification/threads/12345",
            "http-method": "GET"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/threads/12345', 'http-method': 'GET'}) in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertTrue(call().process_thread_event('find_thread') in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 2)

    def test_find_all_threads_endpoint(self):
        event = {
            "resource-path": "/notification/threads",
            "http-method": "GET"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/threads', 'http-method': 'GET'}) in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertTrue(call().process_thread_event('find_all_threads') in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 2)

    def test_find_all_threads_endpoint_qs(self):
        event = {
            "resource-path": "/notification/threads?hello=hi",
            "http-method": "GET"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/threads?hello=hi', 'http-method': 'GET'}) in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertTrue(call().process_thread_event('find_all_threads') in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 2)

    def test_update_thread_endpoint_qs(self):
        event = {
            "resource-path": "/notification/threads/12345",
            "http-method": "PATCH"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/threads/12345', 'http-method': 'PATCH'}) in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertTrue(call().process_thread_event('update_thread') in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 2)

    def test_delete_thread_endpoint(self):
        event = {
            "resource-path": "/notification/threads/12345",
            "http-method": "DELETE"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/threads/12345', 'http-method': 'DELETE'}) in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertTrue(call().process_thread_event('delete_thread') in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 2)

    def test_backfill_endpoint(self):
        event = {
            "resource-path": "/notification/backfill",
            "http-method": "POST"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/backfill', 'http-method': 'POST'}) in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertTrue(call().process_thread_event('backfill_notifications') in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 2)

    def test_async_backfill_endpoint(self):
        real_event = {
            "resource-path": "/notification/backfill_async_trigger",
            "http-method": "POST"
        }
        event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "EventVersion": "1.0",
                    "Sns": {
                        "Type": "Notification",
                        "Subject": "FakeSubjectInvoke",
                        "Message": json.dumps(real_event)
                    }
                }
            ]
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/backfill_async_trigger', 'http-method': 'POST'}) in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertTrue(call().process_thread_event('backfill_notifications_asynchronously') in self.mock_notif_threads.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_threads.mock_calls), 2)
