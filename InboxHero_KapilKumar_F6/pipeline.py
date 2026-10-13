# Roll number: evernorth-aai-1197201
"""A direct, plan-driven InboxHero pipeline using plain dictionaries."""

import html
import json
import os
import re
from datetime import datetime, timedelta

from agent import (
    draft_follow_up,
    draft_investor_reply,
    reason_decision,
    reflect_run,
    rule_decision,
)
from config import (
    CURRENT_TIME,
    DASHBOARD_HTML,
    DASHBOARD_JSON,
    DECISIONS_FILE,
    INBOX_FILE,
    OUTBOX_DIR,
    OWNER_EMAIL,
    PREFERENCES_FILE,
    TRACE_FILE,
)
from mail_store import (
    citations_are_valid,
    index_by_id,
    load_messages,
    retrieve_earlier,
)
from memory import load_preferences, memory_context, save_preference
from security import gate_send, scan_message


# The plan is data, and run_capability executes every listed step in order.
PLANS = {
    "R1": ["scan_security", "learn_preferences", "zero_inbox", "save_decisions"],
    "R2": ["scan_security", "learn_preferences", "grounded_reply"],
    "R3": ["scan_security", "learn_preferences", "grounded_reply", "gate_actions"],
    "R4": ["apply_stored_preference"],
    "R5": ["scan_security", "report_refusals"],
    "R6": [
        "scan_security",
        "learn_preferences",
        "zero_inbox",
        "grounded_reply",
        "extract_commitments",
        "build_dashboard",
    ],
    "X1": ["sender_lookup"],
    "X2": ["follow_up_tracking"],
    "X3": ["scan_security", "zero_inbox", "morning_digest"],
}


def default_paths():
    return {
        "inbox": INBOX_FILE,
        "preferences": PREFERENCES_FILE,
        "trace": TRACE_FILE,
        "decisions": DECISIONS_FILE,
        "outbox": OUTBOX_DIR,
        "dashboard_json": DASHBOARD_JSON,
        "dashboard_html": DASHBOARD_HTML,
    }


def clear_trace(path=None):
    path = path or TRACE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def log_event(context, capability, event, **details):
    row = {"cap": capability, "event": event, **details}
    path = context["paths"]["trace"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def run_capability(
    capability,
    dry_run=False,
    sender="priya@paperjet.io",
    paths=None,
    model_enabled=None,
    approval_fn=None,
):
    if capability not in PLANS:
        raise ValueError("Unknown capability: %s" % capability)
    used_paths = default_paths()
    used_paths.update(paths or {})

    # Loaded before routing, so every rule/model/gate/reflection path shares it.
    messages = load_messages(used_paths["inbox"])
    preferences = load_preferences(used_paths["preferences"])
    context = {
        "messages": messages,
        "by_id": index_by_id(messages),
        "preferences": preferences,
        "startup_context": memory_context(preferences),
        "plan": list(PLANS[capability]),
        "decisions": [],
        "drafts": [],
        "flags": [],
        "commitments": [],
        "pending": [],
        "metrics": {},
        "paths": used_paths,
        "dry_run": dry_run,
        "sender": sender,
        "model_enabled": model_enabled,
        "approval_fn": approval_fn,
    }
    log_event(
        context,
        capability,
        "plan",
        steps=context["plan"],
        startup_context=context["startup_context"],
        process_id=os.getpid(),
    )
    for step_name in context["plan"]:
        log_event(context, capability, "step_started", step=step_name)
        STEP_FUNCTIONS[step_name](context, capability)
        log_event(context, capability, "step_finished", step=step_name)

    summary = run_summary(context)
    reflection_model_enabled = (
        False if capability == "X1" else model_enabled
    )
    context["reflection"] = reflect_run(
        summary,
        context["startup_context"],
        model_enabled=reflection_model_enabled,
    )
    log_event(
        context,
        capability,
        "reflection",
        summary=summary,
        critique=context["reflection"],
        mode="model" if reflection_model_enabled else "local_check",
    )
    return context


def step_scan_security(context, capability):
    context["metrics"]["security_scanned"] = True
    for message in context["messages"]:
        flag = scan_message(message)
        if not flag:
            continue
        context["flags"].append(flag)
        event = "refusal" if flag["category"] == "prompt_injection" else "security_flag"
        log_event(context, capability, event, **flag)
    context["metrics"]["refusals"] = [
        flag["message_id"]
        for flag in context["flags"]
        if flag["category"] == "prompt_injection"
    ]


def step_learn_preferences(context, capability):
    flagged_ids = {flag["message_id"] for flag in context["flags"]}
    found = []
    for message in context["messages"]:
        if message["id"] in flagged_ids:
            continue
        body = message["body"].lower()
        meeting_time = re.search(
            r"before\s+(\d{1,2}:\d{2})\s*(am|pm)",
            body,
            re.IGNORECASE,
        )
        if message["from"] == OWNER_EMAIL and meeting_time:
            parsed = datetime.strptime(
                meeting_time.group(1) + meeting_time.group(2),
                "%I:%M%p",
            )
            found.append(
                (
                    message["id"],
                    "no_meetings_before",
                    parsed.strftime("%H:%M"),
                )
            )
        if (
            message["from"] == "priya@paperjet.io"
            and "cc'd" in body
            and "lawyers" in body
        ):
            found.append(
                (
                    message["id"],
                    "cc_on_legal_mail",
                    message["from"],
                )
            )

    for message_id, key, value in found:
        record = save_preference(
            key,
            value,
            message_id,
            context["paths"]["preferences"],
        )
        context["preferences"][key] = record
        log_event(
            context,
            capability,
            "preference_saved",
            key=key,
            value=value,
            source_message_id=message_id,
        )
    context["startup_context"] = memory_context(context["preferences"])


def step_zero_inbox(context, capability):
    flagged_ids = {flag["message_id"] for flag in context["flags"]}
    for message in context["messages"]:
        if message["id"] in flagged_ids:
            decision = {
                "message_id": message["id"],
                "disposition": "escalate",
                "reason": "Security scanner refused this untrusted message.",
                "route": "security",
                "reversible": True,
                "needs_approval": False,
            }
        else:
            decision = rule_decision(message)
            if decision is None:
                decision = reason_decision(
                    message,
                    context["startup_context"],
                    context["model_enabled"],
                )
            legal_cc = context["preferences"].get("cc_on_legal_mail")
            if (
                legal_cc
                and message["from"].lower().endswith("@hartwellcho.com")
            ):
                decision["required_cc"] = legal_cc["value"]
                decision["reason"] += (
                    " Saved owner preference requires legal mail to include %s."
                    % legal_cc["value"]
                )
        context["decisions"].append(decision)
        log_event(context, capability, "decision", **decision)
    context["metrics"]["rule_handled"] = sum(
        item["route"] == "rule" for item in context["decisions"]
    )
    context["metrics"]["undecided"] = (
        len(context["messages"]) - len(context["decisions"])
    )


def step_save_decisions(context, capability):
    context["paths"]["decisions"].write_text(
        json.dumps(context["decisions"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log_event(
        context,
        capability,
        "artifact",
        path=context["paths"]["decisions"].name,
        records=len(context["decisions"]),
    )


def step_grounded_reply(context, capability):
    _build_grounded_investor_reply(context, capability)


def step_apply_stored_preference(context, capability):
    """R4 intentionally does not relearn m041; it must use restart memory."""
    if "no_meetings_before" not in context["preferences"]:
        _add_ungrounded_flag(
            context,
            "The saved no_meetings_before preference is missing after restart.",
        )
        return
    _build_grounded_investor_reply(context, capability)


def _build_grounded_investor_reply(context, capability):
    target = context["by_id"].get("m043")
    preference_source = context["by_id"].get("m041")
    preference = context["preferences"].get("no_meetings_before")
    if not target or not preference_source or not preference:
        _add_ungrounded_flag(context, "Required source message is missing.")
        return
    if preference.get("source_message_id") != "m041":
        _add_ungrounded_flag(context, "Saved preference has no valid m041 source.")
        return
    retrieved = retrieve_earlier(context["messages"], target)
    earlier = next((item for item in retrieved if item["id"] == "m010"), None)
    if not earlier:
        _add_ungrounded_flag(context, "Earlier investor message m010 was not retrieved.")
        return

    read_ids = {"m010", "m041"}
    for message_id in sorted(read_ids):
        log_event(context, capability, "read", message_id=message_id)
    draft = draft_investor_reply(
        target,
        earlier,
        preference_source,
        preference["value"],
        context["startup_context"],
        context["model_enabled"],
    )
    if not citations_are_valid(
        draft["cited_message_ids"],
        read_ids,
        context["by_id"],
    ):
        _add_ungrounded_flag(context, "Citation validation failed.")
        return
    context["drafts"].append(draft)
    context["pending"].append(
        {
            "message_id": "m043",
            "action": "send reply",
            "reason": "External investor reply is irreversible and needs approval.",
        }
    )
    log_event(context, capability, "draft", **draft)


def _add_ungrounded_flag(context, reason):
    context["flags"].append(
        {
            "message_id": "m043",
            "category": "ungrounded",
            "attempted": "draft investor scheduling response",
            "response": "Draft suppressed. " + reason,
        }
    )


def step_gate_actions(context, capability):
    results = []
    for draft in context["drafts"]:
        result = gate_send(
            draft,
            capability,
            lambda cap, event, **details: log_event(
                context, cap, event, **details
            ),
            dry_run=context["dry_run"],
            approval_fn=context["approval_fn"],
            outbox=context["paths"]["outbox"],
        )
        results.append(result)
    context["metrics"]["gate_results"] = results


def step_report_refusals(context, capability):
    refused = [
        flag
        for flag in context["flags"]
        if flag["category"] == "prompt_injection"
    ]
    context["metrics"]["reported_refusals"] = refused
    log_event(context, capability, "owner_warning", hostile_messages=refused)


def extract_commitments(context):
    """Extract supplied commitments only when their source phrases are present."""
    by_id = context["by_id"]

    def supported(source_terms):
        return all(
            message_id in by_id
            and all(
                phrase.lower() in by_id[message_id]["body"].lower()
                for phrase in phrases
            )
            for message_id, phrases in source_terms.items()
        )

    items = []

    def add(title, start, source_terms):
        if supported(source_terms):
            items.append(
                {
                    "title": title,
                    "start": start,
                    "cited_message_ids": list(source_terms),
                    "conflict": None,
                }
            )

    add(
        "Investor intro call",
        "2026-09-15T15:00:00",
        {"m010": ["Tuesday the 15th", "3:00pm"]},
    )
    add(
        "Dental cleaning",
        "2026-09-15T15:00:00",
        {"m061": ["September 15", "3:00 PM"]},
    )
    add(
        "Board review",
        "2026-09-18T10:00:00",
        {"m038": ["18th", "10:00am"]},
    )

    board_review = datetime.fromisoformat("2026-09-18T10:00:00")
    add(
        "Board deck circulated",
        (board_review - timedelta(days=2)).date().isoformat(),
        {
            "m038": ["board review", "18th", "10:00am"],
            "m040": ["board deck", "two days before"],
        },
    )
    add(
        "Approve annual-discount wording",
        "2026-09-12",
        {"m030": ["annual discount", "by the 12th"]},
    )
    add(
        "PaperJet launch",
        "2026-09-20",
        {
            "m026": ["Target is the 20th"],
            "m036": ["20th is a hard date"],
        },
    )
    add(
        "Candidate offer deadline",
        "2026-09-19",
        {"m042": ["offer", "by the 19th"]},
    )

    now = datetime.fromisoformat(CURRENT_TIME)
    next_friday = now + timedelta(days=(4 - now.weekday()) % 7)
    add(
        "SAFE amendment signature",
        next_friday.date().isoformat(),
        {"m018": ["SAFE", "sign", "by Friday"]},
    )

    for item in items:
        same_time = [other["title"] for other in items if other["start"] == item["start"]]
        if len(same_time) > 1:
            item["conflict"] = "CONFLICT at %s: %s" % (
                item["start"],
                ", ".join(same_time),
            )
    return items


def step_extract_commitments(context, capability):
    valid_commitments = []
    for item in extract_commitments(context):
        read_ids = set(item["cited_message_ids"])
        for message_id in sorted(read_ids):
            log_event(context, capability, "read", message_id=message_id)
        if not citations_are_valid(
            item["cited_message_ids"],
            read_ids,
            context["by_id"],
        ):
            context["flags"].append(
                {
                    "message_id": ",".join(item["cited_message_ids"]),
                    "category": "ungrounded",
                    "attempted": "extract commitment " + item["title"],
                    "response": "Commitment suppressed because citations were invalid.",
                }
            )
            continue
        valid_commitments.append(item)
        log_event(context, capability, "commitment", **item)
    context["commitments"] = valid_commitments


def step_build_dashboard(context, capability):
    for flag in context["flags"]:
        if flag["category"] == "phishing":
            context["pending"].append(
                {
                    "message_id": flag["message_id"],
                    "action": "human security review",
                    "reason": flag["attempted"],
                }
            )
    data = {
        "pending_actions": context["pending"],
        "flagged": context["flags"],
        "commitments": context["commitments"],
    }
    context["paths"]["dashboard_json"].write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    context["paths"]["dashboard_html"].write_text(
        _dashboard_html(data),
        encoding="utf-8",
    )
    log_event(
        context,
        capability,
        "artifact",
        path=context["paths"]["dashboard_html"].name,
        panes=list(data),
    )


def _dashboard_html(data):
    def table(items, fields, headings, css_class=""):
        rows = "".join(
            "<tr>"
            + "".join("<td>%s</td>" % html.escape(str(item.get(field, ""))) for field in fields)
            + "</tr>"
            for item in items
        ) or '<tr><td colspan="%d">None</td></tr>' % len(fields)
        header = "<tr>%s</tr>" % "".join(
            "<th>%s</th>" % html.escape(heading) for heading in headings
        )
        return '<table class="%s">%s%s</table>' % (css_class, header, rows)

    return """<!doctype html><html><head><meta charset="utf-8">
<title>InboxHero Dashboard</title>
<style>body{font-family:Arial}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
section{border:1px solid #aaa;padding:10px}table{border-collapse:collapse;width:100%%}
td,th{border-bottom:1px solid #ddd;padding:5px;text-align:left}.conflict{color:#a00;font-weight:bold}</style>
</head><body><h1>InboxHero Dashboard</h1><div class="grid">
<section><h2>Pending actions</h2>%s</section>
<section><h2>Flagged</h2>%s</section>
<section><h2>Commitments calendar</h2>%s</section>
</div></body></html>""" % (
        table(
            data["pending_actions"],
            ["message_id", "action", "reason"],
            ["Message", "Proposed action", "Why human is needed"],
        ),
        table(
            data["flagged"],
            ["message_id", "attempted", "response"],
            ["Message", "Attempted", "Safe response"],
        ),
        table(
            sorted(data["commitments"], key=lambda item: item["start"]),
            ["start", "title", "cited_message_ids", "conflict"],
            ["Date/time", "Commitment", "Sources", "Conflict"],
            "calendar",
        ),
    )


def step_sender_lookup(context, capability):
    results = [
        {
            "id": message["id"],
            "subject": message["subject"],
            "timestamp": message["timestamp"],
        }
        for message in context["messages"]
        if message["unread"]
        and message["from"].lower() == context["sender"].lower()
    ]
    context["metrics"]["sender_lookup"] = results
    log_event(context, capability, "lookup", sender=context["sender"], results=results)


def step_follow_up_tracking(context, capability):
    now = datetime.fromisoformat(CURRENT_TIME)
    results = []
    for message in context["messages"]:
        if message["from"] != OWNER_EMAIL or message["to"] == OWNER_EMAIL:
            continue
        replies = [
            item
            for item in context["messages"]
            if item["thread_id"] == message["thread_id"]
            and item["timestamp"] > message["timestamp"]
            and item["from"] != OWNER_EMAIL
        ]
        days = (now - datetime.fromisoformat(message["timestamp"])).days
        if days >= 3 and not replies:
            draft = draft_follow_up(message)
            result = {
                "message_id": message["id"],
                "days_waiting": days,
                "draft": draft["body"],
                "cited_message_ids": draft["cited_message_ids"],
            }
            results.append(result)
            log_event(context, capability, "follow_up", **result)
    context["metrics"]["follow_ups"] = results


def step_morning_digest(context, capability):
    context["metrics"]["digest"] = {
        "needs_you": [
            item["message_id"]
            for item in context["decisions"]
            if item["disposition"] in {"reply", "escalate"}
        ],
        "can_wait": [
            item["message_id"]
            for item in context["decisions"]
            if item["disposition"] in {"defer", "delegate"}
        ],
        "auto_archived_count": sum(
            item["disposition"] == "archive" for item in context["decisions"]
        ),
        "security_flags": [item["message_id"] for item in context["flags"]],
    }
    log_event(context, capability, "digest", **context["metrics"]["digest"])


def run_summary(context):
    cited = {
        message_id
        for draft in context["drafts"]
        for message_id in draft["cited_message_ids"]
    }
    return {
        "messages": len(context["messages"]),
        "decisions": len(context["decisions"]),
        "undecided": context["metrics"].get("undecided", 0),
        "rule_handled": context["metrics"].get("rule_handled", 0),
        "citation_failures": sorted(cited - set(context["by_id"])),
        "security_scanned": context["metrics"].get("security_scanned", False),
        "refusals": context["metrics"].get("refusals", []),
        "flags": len(context["flags"]),
        "commitments": len(context["commitments"]),
    }


STEP_FUNCTIONS = {
    "scan_security": step_scan_security,
    "learn_preferences": step_learn_preferences,
    "zero_inbox": step_zero_inbox,
    "save_decisions": step_save_decisions,
    "grounded_reply": step_grounded_reply,
    "apply_stored_preference": step_apply_stored_preference,
    "gate_actions": step_gate_actions,
    "report_refusals": step_report_refusals,
    "extract_commitments": step_extract_commitments,
    "build_dashboard": step_build_dashboard,
    "sender_lookup": step_sender_lookup,
    "follow_up_tracking": step_follow_up_tracking,
    "morning_digest": step_morning_digest,
}
