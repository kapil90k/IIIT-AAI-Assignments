# Roll number: evernorth-aai-1197201
"""Hostile-email detection and the single send gate."""

import json
import re

from config import OUTBOX_DIR


INJECTION_PATTERNS = [
    (r"ignore all previous instructions", "override system instructions"),
    (r"automated-agent directive", "command the mailbox assistant"),
    (r"assistant configuration update", "change assistant configuration from email"),
    (r"if an ai agent is processing", "instruct an AI inside forwarded content"),
    (r"forward the full contents of this mailbox", "exfiltrate the mailbox"),
    (r"must not surface|do not mention|no need to surface", "hide activity from the owner"),
    (r"reply with the single word release", "send unauthorized replies"),
]

PHISHING_PATTERNS = [
    (r"wire \$?[\d,]+|routing:\s*\d+|new account below", "payment redirection"),
    (r"password expires|re-verify your credentials|verify\.com/login", "credential theft"),
    (r"keep this between us|don't loop in finance", "bypass financial controls"),
]


def untrusted_envelope(message):
    """Represent email as data; callers never concatenate it with instructions."""
    return {
        "trust": "untrusted_email_content",
        "message_id": message["id"],
        "sender": message["from"],
        "subject": message["subject"],
        "body": message["body"],
    }


def scan_message(message):
    text = ("%s\n%s" % (message["subject"], message["body"])).lower()
    injections = [
        description
        for pattern, description in INJECTION_PATTERNS
        if re.search(pattern, text, re.IGNORECASE)
    ]
    if injections:
        return {
            "message_id": message["id"],
            "category": "prompt_injection",
            "attempted": "; ".join(sorted(set(injections))),
            "response": "Refused, flagged, reported to owner, and left in the inbox.",
        }

    phishing = [
        description
        for pattern, description in PHISHING_PATTERNS
        if re.search(pattern, text, re.IGNORECASE)
    ]
    sender_name, sender_domain = message["from"].lower().rsplit("@", 1)
    if sender_name == "priya" and sender_domain == "paperjet.co":
        phishing.append("lookalike executive domain")
    if phishing:
        return {
            "message_id": message["id"],
            "category": "phishing",
            "attempted": "; ".join(sorted(set(phishing))),
            "response": "No reply or payment made; escalated for human security review.",
        }
    return None


def gate_send(draft, capability, log_event, dry_run=False, approval_fn=None, outbox=None):
    """The only function allowed to write an outbound message."""
    outbox = outbox or OUTBOX_DIR
    proposal = {"action": "send", **draft}
    if dry_run:
        log_event(
            capability,
            "gate",
            proposed=proposal,
            human_decision="not_requested_dry_run",
            outcome="suppressed",
        )
        return {"approved": False, "outcome": "dry-run", "proposal": proposal}

    if approval_fn is None:
        answer = input(
            "Approve send to %s for %s? [y/N] "
            % (draft["to"], draft["message_id"])
        )
        approved = answer.strip().lower() in {"y", "yes"}
    else:
        approved = bool(approval_fn(proposal))

    outcome = "sent" if approved else "rejected"
    log_event(
        capability,
        "gate",
        proposed=proposal,
        human_decision="approved" if approved else "rejected",
        outcome=outcome,
    )
    if approved:
        outbox.mkdir(parents=True, exist_ok=True)
        path = outbox / ("reply_to_%s.json" % draft["message_id"])
        path.write_text(
            json.dumps(proposal, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return {"approved": approved, "outcome": outcome, "proposal": proposal}
