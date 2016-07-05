import unittest
from mock import patch
import responses
from notification_backend.notification_threads import NotificationThreads
import json
import jwt
from boto3.exceptions import Boto3Error


class TestFindThread(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.notification_threads.dynamodb_results')  # NOQA
        self.addCleanup(patcher1.stop)
        self.mock_db_results = patcher1.start()

        patcher2 = patch('notification_backend.notification_threads.dynamodb_new_item')  # NOQA
        self.addCleanup(patcher2.stop)
        self.mock_db_new_item = patcher2.start()

        self.jwt_signing_secret = "shhsekret"
        self.token = jwt.encode({"sub": "333333"},
                                self.jwt_signing_secret,
                                algorithm='HS256')
        self.lambda_event = {
            "jwt_signing_secret": self.jwt_signing_secret,
            "bearer_token": "Bearer %s" % self.token,
            "payload": {},
            "resource-path": "/notification/threads/12345678",
            "notification_dynamodb_endpoint_url": "http://example.com",
            "notification_user_notification_dynamodb_table_name": "fakethreads"
        }

    def test_invalid_jwt(self):
        self.lambda_event['jwt_signing_secret'] = "shh"
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_thread")
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
        self.lambda_event['bearer_token'] = "Bearer %s" % self.token
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_thread")
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

    def test_empty_auth_header(self):
        self.lambda_event['bearer_token'] = ""
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_thread")
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

    def test_datastore_query_error(self):
        self.mock_db_results.side_effect = Boto3Error
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_thread")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error querying for thread 12345678 from the datastore"
        )
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    def test_single_dynamodb_result(self):
        result = {
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
        }
        self.mock_db_results.return_value.next.return_value = result
        t = NotificationThreads(self.lambda_event)
        result_json = t.process_thread_event("find_thread")
        result_attrs = result_json.get('data').get('data').get('attributes')
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('data').get('type'), "threads")  # NOQA
        self.assertEqual(result_json.get('data').get('data').get('id'), 12345678)  # NOQA
        self.assertEqual(result_attrs.get('thread-url'), "http://api.example.com/fake/12345678")  # NOQA
        self.assertEqual(result_attrs.get('thread-subscription-url'), "http://api.example.com/fake/12345678/subscribe")  # NOQA
        self.assertEqual(result_attrs.get('reason'), "subscribed")
        self.assertEqual(result_attrs.get('updated-at'), 1460443217)
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    @responses.activate
    def test_github_api_400(self):
        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.github.com/notifications/threads/12345678',
            'body': '{"error": "message"}',
            'status': 400
        })
        self.mock_db_results.side_effect = StopIteration
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_thread")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 404)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            404
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Could not find info for thread 12345678"
        )
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    @responses.activate
    def test_github_api_invalid_json(self):
        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.github.com/notifications/threads/12345678',
            'body': 'fake json',
            'status': 200
        })
        self.mock_db_results.side_effect = StopIteration
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_thread")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 404)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            404
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Could not find info for thread 12345678"
        )
        self.assertTrue(self.mock_db_results.mock_calls > 0)

    @responses.activate
    def test_error_persisting_record(self):
        output = {
          "id": "12345678",
          "reason": "manual",
          "updated_at": "2016-04-12T01:40:17Z",
          "subject": {
            "title": "Support AWS APIGateway",
            "url": "https://api.github.com/repos/hashicorp/terraform/issues/3675",  # NOQA
            "latest_comment_url": "https://api.github.com/repos/hashicorp/terraform/issues/comments/208658994",  # NOQA
            "type": "Issue"
          },
          "repository": {
            "id": 17728164,
            "name": "terraform",
            "full_name": "hashicorp/terraform",
            "owner": {
              "login": "hashicorp"
            }
          },
          "url": "https://api.github.com/notifications/threads/12345678",
          "subscription_url": "https://api.github.com/notifications/threads/12345678/subscription"  # NOQA
        }
        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.github.com/notifications/threads/12345678',
            'body': json.dumps(output),
            'status': 200
        })
        self.mock_db_results.side_effect = StopIteration
        self.mock_db_new_item.side_effect = Boto3Error
        t = NotificationThreads(self.lambda_event)
        with self.assertRaises(TypeError) as cm:
            t.process_thread_event("find_thread")
        result_json = json.loads(str(cm.exception))
        self.assertEqual(result_json.get('http_status'), 500)
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('status'),
            500
        )
        self.assertEqual(
            result_json.get('data').get('errors')[0].get('detail'),
            "Error writing info for thread 12345678 to the datastore"
        )
        self.assertTrue(self.mock_db_results.mock_calls > 0)
        self.assertTrue(self.mock_db_new_item.mock_calls > 0)

    @responses.activate
    def test_github_valid_output(self):
        output = {
          "id": "12345678",
          "reason": "manual",
          "updated_at": "2016-04-12T01:40:17Z",
          "subject": {
            "title": "Support AWS APIGateway",
            "url": "https://api.github.com/repos/hashicorp/terraform/issues/3675",  # NOQA
            "latest_comment_url": "https://api.github.com/repos/hashicorp/terraform/issues/comments/208658994",  # NOQA
            "type": "Issue"
          },
          "repository": {
            "id": 17728164,
            "name": "terraform",
            "full_name": "hashicorp/terraform",
            "owner": {
              "login": "hashicorp"
            }
          },
          "url": "https://api.github.com/notifications/threads/12345678",
          "subscription_url": "https://api.github.com/notifications/threads/12345678/subscription"  # NOQA
        }
        responses.add(**{
            'method': responses.GET,
            'url': 'https://api.github.com/notifications/threads/12345678',
            'body': json.dumps(output),
            'status': 200
        })
        self.mock_db_results.side_effect = StopIteration
        t = NotificationThreads(self.lambda_event)
        result_json = t.process_thread_event("find_thread")
        self.assertEqual(result_json.get('http_status'), 200)
        result_attrs = result_json.get('data').get('data').get('attributes')
        self.assertEqual(result_json.get('http_status'), 200)
        self.assertEqual(result_json.get('data').get('data').get('type'), "threads")  # NOQA
        self.assertEqual(result_json.get('data').get('data').get('id'), 12345678)  # NOQA
        self.assertEqual(result_attrs.get('thread-url'), "https://api.github.com/notifications/threads/12345678")  # NOQA
        self.assertEqual(result_attrs.get('thread-subscription-url'), "https://api.github.com/notifications/threads/12345678/subscription")  # NOQA
        self.assertEqual(result_attrs.get('reason'), "manual")
        self.assertEqual(result_attrs.get('updated-at'), 1460425217)
        tags = result_json.get('data').get('data').get('attributes').get('tags')  # NOQA
        self.assertEqual(len(tags), 4)
        self.assertTrue('subscribed' in tags)
        self.assertTrue('issue' in tags)
        self.assertTrue('hashicorp' in tags)
        self.assertTrue('terraform' in tags)
        self.assertTrue(self.mock_db_results.mock_calls > 0)
