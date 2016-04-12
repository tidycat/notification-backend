import unittest
import logging
from mock import patch
from mock import call
from notification_backend.entrypoint import handler
import json


class TestEntrypoint(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.entrypoint.NotificationTags')
        self.addCleanup(patcher1.stop)
        self.mock_notif_tags = patcher1.start()

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
        self.assertEqual(len(self.mock_notif_tags.mock_calls), 0)

    def test_ping_endpoint(self):
        event = {
            "resource-path": "/notification/ping",
            "http-method": "GET"
        }
        result = handler(event, {})
        self.assertEqual(result.get('http_status'), 200)
        self.assertTrue("version" in result.get('data').get('meta'))
        self.assertEqual(len(self.mock_notif_tags.mock_calls), 0)

    def test_get_all_tags_endpoint(self):
        event = {
            "resource-path": "/notification/tags",
            "http-method": "GET"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/tags', 'http-method': 'GET'}) in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertTrue(call().process_tag_event('find_all_tags') in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_tags.mock_calls), 2)

    def test_create_new_tag_endpoint(self):
        event = {
            "resource-path": "/notification/tags",
            "http-method": "POST"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/tags', 'http-method': 'POST'}) in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertTrue(call().process_tag_event('create_new_tag') in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_tags.mock_calls), 2)

    def test_delete_tag_endpoint(self):
        event = {
            "resource-path": "/notification/tags/faketag",
            "http-method": "DELETE"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/tags/faketag', 'http-method': 'DELETE'}) in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertTrue(call().process_tag_event('delete_tag') in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_tags.mock_calls), 2)

    def test_find_tag_endpoint(self):
        event = {
            "resource-path": "/notification/tags/faketag",
            "http-method": "GET"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/tags/faketag', 'http-method': 'GET'}) in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertTrue(call().process_tag_event('find_tag') in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_tags.mock_calls), 2)

    def test_update_tag_endpoint(self):
        event = {
            "resource-path": "/notification/tags/faketag",
            "http-method": "PATCH"
        }
        handler(event, {})
        self.assertTrue(call({'resource-path': '/notification/tags/faketag', 'http-method': 'PATCH'}) in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertTrue(call().process_tag_event('update_tag') in self.mock_notif_tags.mock_calls)  # NOQA
        self.assertEqual(len(self.mock_notif_tags.mock_calls), 2)
