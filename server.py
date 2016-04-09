import BaseHTTPServer
import sys
import time
import json
import os
import re
from notification_backend.entrypoint import handler


HOST_NAME = sys.argv[1]
PORT_NUMBER = int(sys.argv[2])


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


def handle_request(payload, headers, resource_path, http_method):
    token_header = re.match('^Bearer (.+)', headers.get("Authorization"))
    event = {
        "resource-path": resource_path,
        "payload": payload,
        "http-method": http_method,
        "jwt_signing_secret": "supersekr3t",
        "bearer_token": token_header.group(1),
        "notification_dynamodb_endpoint_url": os.environ['DYNAMODB_ENDPOINT_URL'],  # NOQA
        "notification_tags_dynamodb_table_name": os.environ['NOTIFICATION_TAGS_DYNAMODB_TABLE_NAME']  # NOQA
    }
    try:
        response_payload = handler(event, {})
        return transform_response(response_payload)
    except TypeError as e:
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
