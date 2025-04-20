from config import Config
import requests
import logging
import json


# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def post_conversation_update(call_sid: str, new_messages: list) -> bool:
    """
    POSTs the latest messages to the front-end conversation webhook.
    Returns True if the update was accepted (2xx), False otherwise.

    Args:
        call_sid (str): Unique identifier for the call/conversation.
        new_messages (list): List of message dicts to send (e.g. [{'role': 'user', 'content': '...'}]).
    """
    # Normalize URL: avoid trailing slash mismatches
    url = Config.APP_PUBLIC_CONVERSATION_URL.rstrip('/')
    payload = {
        "call_sid": call_sid,
        "new_messages": new_messages
    }

    try:
        logger.info(f"Posting conversation update to {url}")
        logger.debug(f"Payload: {payload!r}")

        # Use requests.json helper to encode payload and set Content-Type
        response = requests.post(
            url,
            json=payload,
            headers={"Accept": "application/json"},
            timeout=10
        )

        logger.info(f"Webhook response code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response body: {response.text}")

        # Raise for HTTP errors (4xx, 5xx)
        response.raise_for_status()
        return True

    except requests.exceptions.HTTPError as http_err:
        # Log body for debugging (e.g., 404 Not Found)
        body = response.text if 'response' in locals() else 'No response body'
        logger.error(f"HTTPError sending conversation update: {http_err} — Body: {body}")
    except requests.exceptions.RequestException as req_err:
        # Covers connection errors, timeouts, etc.
        logger.error(f"RequestException sending conversation update: {req_err}")
    except Exception as err:
        # Unexpected errors
        logger.error(f"Unexpected error in post_conversation_update: {err}", exc_info=True)

    return False
