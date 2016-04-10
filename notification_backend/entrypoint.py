import logging
import re
from notification_backend.notification_tags import NotificationTags
from notification_backend.http import format_response
from notification_backend.http import format_error_payload

__version__ = "0.0.1"
logging.basicConfig()
logger = logging.getLogger("notification_backend")
logger.setLevel(logging.DEBUG)


def handler(event, context):
    logger.debug("Received event: %s" % event)
    resource_path = event.get('resource-path')
    http_method = event.get('http-method')
    tag_name_path = re.match('^/tags/(.+)', resource_path)

    if http_method == "GET" and resource_path == "/tags":
        logger.debug("Getting a list of all tags")
        tags = NotificationTags(event)
        return tags.process_tag_event("find_all_tags")

    elif http_method == "GET" and tag_name_path:
        logger.debug("Getting info about tag: %s" % tag_name_path.group(1))
        return format_response(200, {"data": []})

    elif http_method == "PATCH" and tag_name_path:
        logger.debug("Updating tag: %s" % tag_name_path.group(1))
        return format_response(200, {"data": []})

    elif http_method == "POST" and resource_path == "/tags":
        logger.debug("Creating a new tag")
        return format_response(200, {"data": []})

    elif http_method == "DELETE" and tag_name_path:
        logger.debug("Deleting tag: %s" % tag_name_path.group(1))
        return format_response(200, {"data": []})

    payload = format_error_payload(400, "Invalid path %s" % resource_path)
    return format_response(400, payload)
