import unittest
from mock import patch
from mock import call
from notification_backend.http import dynamodb_results
from notification_backend.http import dynamodb_new_item
from notification_backend.http import dynamodb_delete_item
from notification_backend.http import dynamodb_update_item


class TestHttp(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('notification_backend.http.boto3.resource')
        self.addCleanup(patcher1.stop)
        self.mock_boto = patcher1.start()

    def test_db_results_no_index_name(self):
        mock_results = [
            {
                "Items": [
                    {"one": "item one"}
                ]
            }
        ]
        self.mock_boto.return_value.Table.return_value.query.side_effect = mock_results  # NOQA
        results = dynamodb_results(endpoint_url="endpoint",
                                   table_name="table",
                                   key="key")
        result = results.next()
        self.assertEqual(self.mock_boto.return_value.Table.return_value.query.mock_calls,  # NOQA
                         [call(KeyConditionExpression='key')])
        self.assertEqual(result, {"one": "item one"})
        with self.assertRaises(StopIteration):
            results.next()

    def test_db_results_paginated(self):
        mock_results = [
            {
                "Items": [
                    {"one": "item one"}
                ],
                "LastEvaluatedKey": "paginationkey"
            },
            {
                "Items": [
                    {"two": "item two"}
                ]
            }
        ]
        self.mock_boto.return_value.Table.return_value.query.side_effect = mock_results  # NOQA
        results = dynamodb_results(endpoint_url="endpoint",
                                   table_name="table",
                                   key="key",
                                   index_name="index")
        result = results.next()
        self.assertEqual(self.mock_boto.return_value.Table.return_value.query.mock_calls,  # NOQA
                         [call(KeyConditionExpression='key', IndexName='index')])  # NOQA
        self.assertEqual(result, {"one": "item one"})
        result = results.next()
        self.assertEqual(len(self.mock_boto.return_value.Table.return_value.query.mock_calls), 2)  # NOQA
        self.assertTrue(call(KeyConditionExpression='key', IndexName='index') in self.mock_boto.return_value.Table.return_value.query.mock_calls)  # NOQA
        self.assertTrue(call(KeyConditionExpression='key', IndexName='index', ExclusiveStartKey='paginationkey') in self.mock_boto.return_value.Table.return_value.query.mock_calls)  # NOQA
        self.assertEqual(result, {"two": "item two"})

    def test_db_new_item_no_condition_expression(self):
        dynamodb_new_item(endpoint_url="endpoint",
                          table_name="table",
                          item="item")
        self.assertEqual(self.mock_boto.return_value.Table.return_value.put_item.mock_calls, [call(Item='item')])  # NOQA

    def test_db_new_item(self):
        dynamodb_new_item(endpoint_url="endpoint",
                          table_name="table",
                          item="item",
                          condition_expression="condition")
        self.assertEqual(self.mock_boto.return_value.Table.return_value.put_item.mock_calls, [call(Item='item', ConditionExpression="condition")])  # NOQA

    def test_db_delete_item(self):
        dynamodb_delete_item(endpoint_url="endpoint",
                             table_name="table",
                             key="key",
                             condition_expression="condition")
        self.assertEqual(self.mock_boto.return_value.Table.return_value.delete_item.mock_calls, [call(Key='key', ConditionExpression="condition")])  # NOQA

    def test_db_update_item_no_condition_expression(self):
        dynamodb_update_item(endpoint_url="endpoint",
                             table_name="table",
                             key="key",
                             update_expression="updateexpression",
                             expr_attribute_values="exprvalues")
        self.assertEqual(self.mock_boto.return_value.Table.return_value.update_item.mock_calls,  # NOQA
                         [call(Key='key', UpdateExpression='updateexpression', ExpressionAttributeValues='exprvalues', ReturnValues='UPDATED_NEW')])  # NOQA

    def test_db_update_item(self):
        dynamodb_update_item(endpoint_url="endpoint",
                             table_name="table",
                             key="key",
                             update_expression="updateexpression",
                             expr_attribute_values="exprvalues",
                             condition_expression="condition")
        self.assertEqual(self.mock_boto.return_value.Table.return_value.update_item.mock_calls,  # NOQA
                         [call(Key='key', UpdateExpression='updateexpression', ExpressionAttributeValues='exprvalues', ReturnValues='UPDATED_NEW', ConditionExpression='condition')])  # NOQA
