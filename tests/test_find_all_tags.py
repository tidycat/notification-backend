import unittest
from mock import patch
from notification_backend.notification_tags import NotificationTags
import json
import jwt
from boto3.exceptions import Boto3Error


class TestFindAllTags(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_tags.dynamodb_results')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_results = patcher1.start()

        self.jwt_signing_secret = "shhsekret"
        self.token = jwt.encode({"sub": "user1"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event = {
            "jwt_signing_secret": self.jwt_signing_secret,
            "bearer_token": self.token,
            "payload": {
                "token": self.token
            },
            "notification_dynamodb_endpoint_url": "http://example.com",
            "notification_tags_dynamodb_table_name": "faketags"
        }

    def test_invalid_jwt(self):
        self.lambda_event['jwt_signing_secret'] = "shh"
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("find_all_tags")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 401)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            401
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Invalid JSON Web Token"
        )

    def test_invalid_userid(self):
        self.token = jwt.encode({"subs": "user1"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event['bearer_token'] = self.token
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("find_all_tags")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 401)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            401
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "sub field not present in JWT"
        )

    def test_datastore_query_error(self):
        self.mock_db_results.side_effect = Boto3Error
        t = NotificationTags(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_tag_event("find_all_tags")
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
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    def test_empty_result_list(self):
        self.mock_db_results.return_value = []
        t = NotificationTags(self.lambda_event)
        result_json = t.process_tag_event("find_all_tags")
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('data'), [])
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    def test_single_result(self):
        self.mock_db_results.return_value = [
            {"tag_name": "doing", "tag_color": "blue"}
        ]
        expected_result = [
            {
                "id": "doing",
                "type": "tags",
                "attributes": {
                    "color": "blue"
                }
            }
        ]
        t = NotificationTags(self.lambda_event)
        result_json = t.process_tag_event("find_all_tags")
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('data'), expected_result)
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    def test_multiple_results(self):
        self.mock_db_results.return_value = [
            {"tag_name": "doing", "tag_color": "blue"},
            {"tag_name": "done", "tag_color": "red"}
        ]
        res0 = {
            "id": "done",
            "type": "tags",
            "attributes": {
                "color": "red"
            }
        }
        res1 = {
            "id": "doing",
            "type": "tags",
            "attributes": {
                "color": "blue"
            }
        }
        t = NotificationTags(self.lambda_event)
        result_json = t.process_tag_event("find_all_tags")
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(len(result_json.get('data').get('data')), 2)
        self.assertTrue(res0 in result_json.get('data').get('data'))
        self.assertTrue(res1 in result_json.get('data').get('data'))
        self.assertTrue(self.mock_db_results.mock_calls > 0)
