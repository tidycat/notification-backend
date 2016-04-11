import unittest
from mock import patch
from notification_backend.notification_tags import NotificationTags
import json
import jwt
from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError


class TestCreateNewTag(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_tags.dynamodb_new_item')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_item = patcher1.start()

        self.jwt_signing_secret = "shhsekret"
        self.token = jwt.encode({"sub": "user1"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event = {
            "jwt_signing_secret": self.jwt_signing_secret,
            "bearer_token": self.token,
            "payload": {
                "data": {
                    "id": "wiptag",
                    "type": "tags",
                    "attributes": {
                        "color": "#aaaaaa"
                    }
                }
            },
            "notification_dynamodb_endpoint_url": "http://example.com",
            "notification_tags_dynamodb_table_name": "faketags"
        }

    def test_missing_type_member(self):
        self.lambda_event['payload']['data'].pop("type")
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 400)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            400
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Payload missing 'type' member"
        )
        self.assertEqual(self.mock_db_item.mock_calls, [])

    def test_invalid_type_member(self):
        self.lambda_event['payload']['data']['type'] = "faketags"
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 400)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            400
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Payload missing 'type' member"
        )
        self.assertEqual(self.mock_db_item.mock_calls, [])

    def test_missing_tag_id(self):
        self.lambda_event['payload']['data'].pop("id")
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 400)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            400
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Payload missing 'id' member"
        )
        self.assertEqual(self.mock_db_item.mock_calls, [])

    def test_tag_already_exists(self):
        ce = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "OperationName")  # NOQA
        self.mock_db_item.side_effect = ce
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 409)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            409
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Tag wiptag already exists"
        )
        self.assertTrue(self.mock_db_item.mock_calls > 0)

    def test_error_querying_datastore_clienterror(self):
        ce = ClientError({"Error": {"Code": "randomfake"}}, "OperationName")  # NOQA
        self.mock_db_item.side_effect = ce
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
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
        self.assertTrue(self.mock_db_item.mock_calls > 0)

    def test_error_querying_datastore_boto3error(self):
        self.mock_db_item.side_effect = Boto3Error
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
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
        self.assertTrue(self.mock_db_item.mock_calls > 0)

    def test_create_new_tag(self):
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 201)
        self.assertEqual(result_json.get('data').get('data').get('type'),
                         'tags')
        self.assertEqual(result_json.get('data').get('data').get('id'),
                         'wiptag')
        self.assertEqual(
            result_json.get('data').get('data').get('attributes').get('color'),
            '#aaaaaa'
        )
        self.assertTrue(self.mock_db_item.mock_calls > 0)

    def test_create_new_tag_default_color(self):
        self.lambda_event['payload']['data']['attributes'].pop("color")
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("create_new_tag")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 201)
        self.assertEqual(result_json.get('data').get('data').get('type'),
                         'tags')
        self.assertEqual(result_json.get('data').get('data').get('id'),
                         'wiptag')
        self.assertEqual(
            result_json.get('data').get('data').get('attributes').get('color'),
            '#ffffff'
        )
        self.assertTrue(self.mock_db_item.mock_calls > 0)
