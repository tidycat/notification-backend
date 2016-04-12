import unittest
from mock import patch
from notification_backend.notification_tags import NotificationTags
import json
import jwt
from boto3.exceptions import Boto3Error


class TestFindTag(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_tags.dynamodb_get_item')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_find = patcher1.start()

        self.jwt_signing_secret = "shhsekret"
        self.token = jwt.encode({"sub": "user1"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event = {
            "jwt_signing_secret": self.jwt_signing_secret,
            "bearer_token": self.token,
            "payload": {},
            "resource-path": "/notification/tags/wiptag",
            "notification_dynamodb_endpoint_url": "http://example.com",
            "notification_tags_dynamodb_table_name": "faketags"
        }

    def test_error_querying_datastore(self):
        self.mock_db_find.side_effect = Boto3Error
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("find_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error getting tag wiptag from the datastore"
        )
        self.assertTrue(self.mock_db_find.mock_calls > 0)

    def test_tag_does_not_exist(self):
        self.mock_db_find.return_value = {}
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("find_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 404)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            404
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Could not find information for tag wiptag"
        )
        self.assertTrue(self.mock_db_find.mock_calls > 0)

    def test_find_tag(self):
        self.mock_db_find.return_value = {
            "tag_name": "wiptag",
            "tag_color": "red",
        }
        t = NotificationTags(self.lambda_event)
        result_json = t.process_tag_event("find_tag")
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('data').get('id'),
                         'wiptag')
        self.assertEqual(result_json.get('data').get('data').get('type'),
                         'tags')
        self.assertEqual(result_json.get('data').get('data').get('attributes').get('color'),  # NOQA
                         'red')
        self.assertTrue(self.mock_db_find.mock_calls > 0)
