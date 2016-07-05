import logging
from notification_backend.notification_threads import NotificationThreads
from notification_backend.http import format_response
from notification_backend.http import format_error_payload

__version__ = "0.0.1"
logging.basicConfig()
logger = logging.getLogger("notification_backend")
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.debug("Received event: %s" % event)

    resource_path = event.get('resource-path')
    http_method = event.get('http-method')

    if http_method == "GET" and resource_path == "/notification/threads":
        logger.debug("Getting a list of all threads")
        t = NotificationThreads(event)
        return t.process_thread_event("find_all_threads")

    elif http_method == "GET" and resource_path == "/notification/threads/{thread-id}":  # NOQA
        logger.debug("Getting info about thread: %s" % event.get('threadid'))
        t = NotificationThreads(event)
        return t.process_thread_event("find_thread")

    elif http_method == "PATCH" and resource_path == "/notification/threads/{thread-id}":  # NOQA
        logger.debug("Updating thread: %s" % event.get('threadid'))
        t = NotificationThreads(event)
        return t.process_thread_event("update_thread")

    elif http_method == "DELETE" and resource_path == "/notification/threads/{thread-id}":  # NOQA
        logger.debug("Deleting thread: %s" % event.get('threadid'))
        t = NotificationThreads(event)
        return t.process_thread_event("delete_thread")

    elif http_method == "GET" and resource_path == "/notification/ping":
        payload = {
            "data": [],
            "meta": {
                "version": __version__
            }
        }
        return format_response(200, payload)

    payload = format_error_payload(400, "Invalid path %s" % resource_path)
    return format_response(400, payload)
