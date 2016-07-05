import BaseHTTPServer
import sys
import time
import json
import os
import logging
import re
from notification_backend.entrypoint import handler


HOST_NAME = sys.argv[1]
PORT_NUMBER = int(sys.argv[2])
logger = logging.getLogger("notification_backend")

allowed_headers = [
    "Content-Type",
    "Authorization"
]

allowed_methods = [
    "OPTIONS",
    "GET",
    "POST",
    "PATCH",
    "DELETE"
]


class LocalNotificationBackend(BaseHTTPServer.BaseHTTPRequestHandler):

    server_version = "LocalNotificationBackend/0.1"

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Methods", ",".join(allowed_methods))  # NOQA
        self.send_header("Access-Control-Allow-Headers", ",".join(allowed_headers))  # NOQA
        self.end_headers()

    def do_GET(self):
        status, result = handle_request({}, self.headers, self.path, "GET")
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Methods", ",".join(allowed_methods))  # NOQA
        self.send_header("Access-Control-Allow-Headers", ",".join(allowed_headers))  # NOQA
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
        self.send_header("Access-Control-Allow-Methods", ",".join(allowed_methods))  # NOQA
        self.send_header("Access-Control-Allow-Headers", ",".join(allowed_headers))  # NOQA
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
        self.send_header("Access-Control-Allow-Methods", ",".join(allowed_methods))  # NOQA
        self.send_header("Access-Control-Allow-Headers", ",".join(allowed_headers))  # NOQA
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result))

    def do_DELETE(self):
        status, result = handle_request({}, self.headers, self.path, "DELETE")
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Access-Control-Allow-Methods", ",".join(allowed_methods))  # NOQA
        self.send_header("Access-Control-Allow-Headers", allowed_headers.join(","))  # NOQA
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result))


def handle_request(payload, headers, resource_path, http_method):
    threadid = None
    thread_id_path = re.match('^/notification/threads/([0-9]+)$', resource_path)  # NOQA
    if thread_id_path:
        resource_path = "/notification/threads/{thread-id}"
        threadid = thread_id_path.group(1)

    qs_from = None
    # qs_from_path = re.match('^/notification/threads(\?.+)?$', resource_path)
    qs_from_path = re.match('^/notification/threads\?from=(.+)$', resource_path)  # NOQA
    if qs_from_path:
        resource_path = "/notification/threads"
        qs_from = qs_from_path.group(1)

    event = {
        "resource-path": resource_path,
        "payload": payload,
        "http-method": http_method,
        "jwt_signing_secret": "supersekr3t",
        "bearer_token": headers.get("Authorization"),
        "notification_dynamodb_endpoint_url": os.environ['DYNAMODB_ENDPOINT_URL'],  # NOQA
        "notification_user_notification_dynamodb_table_name": os.environ['NOTIFICATION_USER_NOTIFICATION_DYNAMODB_TABLE_NAME'],  # NOQA
        "notification_user_notification_date_dynamodb_index_name": os.environ['NOTIFICATION_USER_NOTIFICATION_DATE_DYNAMODB_INDEX_NAME'],  # NOQA
        "threadid": threadid,
        "qs_from": qs_from,
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
