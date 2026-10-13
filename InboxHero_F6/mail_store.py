# Roll number: evernorth-aai-1197201
"""Simple read-only inbox loading and retrieval functions."""

import json
import re

from config import INBOX_FILE


def load_messages(path=None):
    """Load the supplied inbox as a list of normal dictionaries."""
    path = path or INBOX_FILE
    return json.loads(path.read_text(encoding="utf-8"))


def index_by_id(messages):
    return {message["id"]: message for message in messages}


def retrieve_earlier(messages, current_message):
    """Walk the thread first; use keyword search only when the thread is empty."""
    earlier = [
        message
        for message in messages
        if message["thread_id"] == current_message["thread_id"]
        and message["timestamp"] < current_message["timestamp"]
    ]
    if earlier:
        return sorted(earlier, key=lambda message: message["timestamp"])

    query = current_message["subject"] + " " + current_message["body"]
    tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9@.:-]+", query)
        if len(token) > 3
    }
    scored = []
    for message in messages:
        if message["timestamp"] >= current_message["timestamp"]:
            continue
        text = (
            message["subject"] + " " + message["body"] + " " + message["from"]
        ).lower()
        score = sum(token in text for token in tokens)
        if score:
            scored.append((score, message["timestamp"], message))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[2] for row in scored[:10]]


def citations_are_valid(cited_ids, read_ids, messages_by_id):
    return bool(cited_ids) and all(
        message_id in messages_by_id and message_id in read_ids
        for message_id in cited_ids
    )
