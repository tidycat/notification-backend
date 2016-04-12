import unittest
from mock import patch
from notification_backend.notification_tags import NotificationTags
import json
import jwt
from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError


class TestDeleteTag(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_tags.dynamodb_delete_item')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_delete = patcher1.start()

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

    def test_tag_does_not_exist(self):
        ce = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "OperationName")  # NOQA
        self.mock_db_delete.side_effect = ce
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("delete_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 409)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            409
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Tag wiptag does not exist"
        )
        self.assertTrue(self.mock_db_delete.mock_calls > 0)

    def test_error_querying_datastore_clienterror(self):
        ce = ClientError({"Error": {"Code": "randomfake"}}, "OperationName")  # NOQA
        self.mock_db_delete.side_effect = ce
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("delete_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error deleting tag wiptag from the datastore"
        )
        self.assertTrue(self.mock_db_delete.mock_calls > 0)

    def test_error_querying_datastore_boto3error(self):
        self.mock_db_delete.side_effect = Boto3Error
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("delete_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error deleting tag wiptag from the datastore"
        )
        self.assertTrue(self.mock_db_delete.mock_calls > 0)

    def test_delete_tag(self):
        t = NotificationTags(self.lambda_event)
        result_json = t.process_tag_event("delete_tag")
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('meta').get('message'),
                         'Tag wiptag successfully deleted')
        self.assertTrue(self.mock_db_delete.mock_calls > 0)
