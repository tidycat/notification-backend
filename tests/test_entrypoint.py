import unittest
import logging
from mock import patch
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
