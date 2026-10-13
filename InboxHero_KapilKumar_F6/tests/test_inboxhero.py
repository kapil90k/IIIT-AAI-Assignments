# Roll number: evernorth-aai-1197201

import json

import agent
from mail_store import load_messages
from memory import load_preferences, save_preference
from pipeline import run_capability
from security import gate_send, scan_message


def paths(tmp_path):
    return {
        "preferences": tmp_path / "preferences.json",
        "trace": tmp_path / "trace.jsonl",
        "decisions": tmp_path / "decisions.json",
        "outbox": tmp_path / "outbox",
        "dashboard_json": tmp_path / "dashboard.json",
        "dashboard_html": tmp_path / "dashboard.html",
    }


def test_inbox_has_100_messages():
    messages = load_messages()
    assert len(messages) == 100
    assert len({message["id"] for message in messages}) == 100


def test_r1_zeroes_every_message(tmp_path):
    result = run_capability("R1", paths=paths(tmp_path), model_enabled=False)
    ids = [item["message_id"] for item in result["decisions"]]
    assert len(ids) == 100
    assert len(set(ids)) == 100
    assert result["metrics"]["undecided"] == 0
    assert result["metrics"]["rule_handled"] == 51
    legal = next(
        item for item in result["decisions"] if item["message_id"] == "m018"
    )
    assert legal["required_cc"] == "priya@paperjet.io"


def test_hostile_and_phishing_messages_are_found():
    flags = [scan_message(message) for message in load_messages()]
    flags = [flag for flag in flags if flag]
    injections = {
        flag["message_id"]
        for flag in flags
        if flag["category"] == "prompt_injection"
    }
    phishing = {
        flag["message_id"] for flag in flags if flag["category"] == "phishing"
    }
    assert {"m017", "m024", "m039", "m047"} <= injections
    assert {"m021", "m023", "m045"} <= phishing


def test_r2_draft_is_grounded_and_reads_sources(tmp_path):
    result = run_capability("R2", paths=paths(tmp_path), model_enabled=False)
    draft = result["drafts"][0]
    assert draft["cited_message_ids"] == ["m010", "m041"]
    assert "Tuesday the 15th" in draft["body"]
    assert "3:00pm" in draft["body"]
    assert "11:00" in draft["body"]
    events = [
        json.loads(line)
        for line in (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    reads = {event["message_id"] for event in events if event["event"] == "read"}
    assert set(draft["cited_message_ids"]) <= reads


def test_missing_grounding_suppresses_draft(tmp_path):
    inbox = [
        message for message in load_messages() if message["id"] != "m010"
    ]
    inbox_path = tmp_path / "inbox.json"
    inbox_path.write_text(json.dumps(inbox), encoding="utf-8")
    custom_paths = paths(tmp_path)
    custom_paths["inbox"] = inbox_path
    result = run_capability("R2", paths=custom_paths, model_enabled=False)
    assert result["drafts"] == []
    assert any(flag["category"] == "ungrounded" for flag in result["flags"])


def test_dry_run_gate_writes_nothing(tmp_path):
    events = []
    draft = {
        "message_id": "m043",
        "to": "investor@example.com",
        "cc": [],
        "subject": "Re: meeting",
        "body": "Draft",
        "cited_message_ids": ["m010"],
    }
    result = gate_send(
        draft,
        "R3",
        lambda cap, event, **details: events.append(details),
        dry_run=True,
        outbox=tmp_path / "outbox",
    )
    assert result["outcome"] == "dry-run"
    assert not (tmp_path / "outbox").exists()
    assert events == [
        {
            "proposed": result["proposal"],
            "human_decision": "not_requested_dry_run",
            "outcome": "suppressed",
        }
    ]


def test_approved_gate_writes_exactly_one_file(tmp_path):
    draft = {
        "message_id": "m043",
        "to": "investor@example.com",
        "cc": [],
        "subject": "Re: meeting",
        "body": "Approved draft",
        "cited_message_ids": ["m010", "m041"],
    }
    outbox = tmp_path / "outbox"
    result = gate_send(
        draft,
        "R3",
        lambda *args, **kwargs: None,
        approval_fn=lambda proposal: True,
        outbox=outbox,
    )
    assert result["outcome"] == "sent"
    assert [item.name for item in outbox.iterdir()] == ["reply_to_m043.json"]


def test_preference_survives_reload(tmp_path):
    path = tmp_path / "preferences.json"
    save_preference("no meetings before", "11:00", "m041", path)
    assert load_preferences(path)["no_meetings_before"]["value"] == "11:00"


def test_r4_requires_and_applies_restart_memory(tmp_path):
    custom_paths = paths(tmp_path)
    without_memory = run_capability(
        "R4",
        paths=custom_paths,
        model_enabled=False,
    )
    assert without_memory["drafts"] == []
    save_preference(
        "no meetings before",
        "11:00",
        "m041",
        custom_paths["preferences"],
    )
    with_memory = run_capability(
        "R4",
        paths=custom_paths,
        model_enabled=False,
    )
    assert with_memory["drafts"]
    assert "11:00" in with_memory["drafts"][0]["body"]


def test_commitments_include_multi_source_and_conflict(tmp_path):
    result = run_capability("R6", paths=paths(tmp_path), model_enabled=False)
    assert any(len(item["cited_message_ids"]) > 1 for item in result["commitments"])
    conflicts = {item["title"] for item in result["commitments"] if item["conflict"]}
    assert conflicts == {"Investor intro call", "Dental cleaning"}
    date_only = {
        item["title"]: item["start"]
        for item in result["commitments"]
        if item["title"]
        in {
            "Approve annual-discount wording",
            "PaperJet launch",
            "Candidate offer deadline",
            "SAFE amendment signature",
        }
    }
    assert all("T" not in start for start in date_only.values())


def test_r5_reports_injections(tmp_path):
    inbox_path = tmp_path / "inbox.json"
    original = json.dumps(load_messages(), indent=2)
    inbox_path.write_text(original, encoding="utf-8")
    custom_paths = paths(tmp_path)
    custom_paths["inbox"] = inbox_path
    result = run_capability("R5", paths=custom_paths, model_enabled=False)
    reported = {
        item["message_id"] for item in result["metrics"]["reported_refusals"]
    }
    assert {"m017", "m024", "m039", "m047"} <= reported
    assert inbox_path.read_text(encoding="utf-8") == original
    assert not custom_paths["outbox"].exists()


def test_dashboard_has_exactly_three_panes(tmp_path):
    run_capability("R6", paths=paths(tmp_path), model_enabled=False)
    data = json.loads((tmp_path / "dashboard.json").read_text(encoding="utf-8"))
    html = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert set(data) == {"pending_actions", "flagged", "commitments"}
    assert html.count("<section>") == 3


def test_follow_up_finds_m044_but_not_answered_m003(tmp_path):
    result = run_capability("X2", paths=paths(tmp_path), model_enabled=False)
    ids = {item["message_id"] for item in result["metrics"]["follow_ups"]}
    assert "m044" in ids
    assert "m003" not in ids


def test_x1_never_calls_model_even_when_model_is_enabled(monkeypatch, tmp_path):
    calls = []

    def fake_model(*args, **kwargs):
        calls.append((args, kwargs))
        return {"critique": "unexpected", "confidence": "low"}

    monkeypatch.setattr(agent, "ask_model", fake_model)
    run_capability("X1", paths=paths(tmp_path), model_enabled=True)
    assert calls == []


def test_plan_steps_execute_before_reflection(tmp_path):
    result = run_capability("R1", paths=paths(tmp_path), model_enabled=False)
    events = [
        json.loads(line)
        for line in (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events[0]["event"] == "plan"
    started = [event["step"] for event in events if event["event"] == "step_started"]
    assert started == result["plan"]
    assert events[-1]["event"] == "reflection"


def test_model_path_can_choose_and_reflect(monkeypatch):
    def fake_model(system, payload, model_enabled=None):
        if "Review this completed run" in system:
            return {"critique": "Reviewed after execution.", "confidence": "high"}
        return {"disposition": "defer", "reason": "Model chose to wait."}

    monkeypatch.setattr(agent, "ask_model", fake_model)
    message = load_messages()[2]
    decision = agent.reason_decision(message, "startup context", model_enabled=True)
    reflection = agent.reflect_run({}, "startup context", model_enabled=True)
    assert decision["route"] == "model"
    assert "Reviewed after" in reflection
