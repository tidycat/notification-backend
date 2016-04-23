import BaseHTTPServer
import sys
import time
import json
import os
import re
import logging
from mock import patch
from notification_backend.entrypoint import handler


HOST_NAME = sys.argv[1]
PORT_NUMBER = int(sys.argv[2])
logger = logging.getLogger("notification_backend")


class LocalNotificationBackend(BaseHTTPServer.BaseHTTPRequestHandler):

    server_version = "LocalNotificationBackend/0.1"

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        status, result = handle_request({}, self.headers, self.path, "GET")
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result))

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(length)
        payload = json.loads(post_data)
        status, result = handle_request(
            payload,
            self.headers,
            self.path,
            "POST"
        )
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result))

    def do_PATCH(self):
        length = int(self.headers['Content-Length'])
        patch_data = self.rfile.read(length)
        payload = json.loads(patch_data)
        status, result = handle_request(
            payload,
            self.headers,
            self.path,
            "PATCH"
        )
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result))

    def do_DELETE(self):
        status, result = handle_request({}, self.headers, self.path, "DELETE")
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result))


def fake_sns_message(event, context, topic_arn):
    logger.info("Publishing fake SNS message for endpoint: %s" % event.get('resource-path'))  # NOQA
    sns_event = {
        "Records": [
            {
                "EventSource": "aws:sns",
                "EventVersion": "1.0",
                "Sns": {
                    "Type": "Notification",
                    "Subject": "FakeSubjectInvoke",
                    "Message": json.dumps(event)
                }
            }
        ]
    }
    handler(sns_event, {})


@patch('notification_backend.notification_threads.send_sns_message', fake_sns_message)  # NOQA
def handle_request(payload, headers, resource_path, http_method):
    token_header = re.match('^Bearer (.+)',
                            headers.get("Authorization", "Bearer faketoken"))
    event = {
        "resource-path": resource_path,
        "payload": payload,
        "http-method": http_method,
        "jwt_signing_secret": "supersekr3t",
        "bearer_token": token_header.group(1),
        "notification_dynamodb_endpoint_url": os.environ['DYNAMODB_ENDPOINT_URL'],  # NOQA
        "notification_tags_dynamodb_table_name": os.environ['NOTIFICATION_TAGS_DYNAMODB_TABLE_NAME'],  # NOQA
        "notification_user_notification_dynamodb_table_name": os.environ['NOTIFICATION_USER_NOTIFICATION_DYNAMODB_TABLE_NAME'],  # NOQA
        "notification_user_notification_date_dynamodb_index_name": os.environ['NOTIFICATION_USER_NOTIFICATION_DATE_DYNAMODB_INDEX_NAME'],  # NOQA
        "notification_sns_arn": "notification-sns-arn",
    }
    try:
        response_payload = handler(event, {})
        logger.debug("Server Response: %s" % response_payload)
        return transform_response(response_payload)
    except TypeError as e:
        logger.debug("Server error Response: %s" % str(e))
        return transform_response(json.loads(str(e)))


def transform_response(response_payload):
    status = response_payload['http_status']
    data = response_payload['data']
    return (status, data)


if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), LocalNotificationBackend)
    print(time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER))
