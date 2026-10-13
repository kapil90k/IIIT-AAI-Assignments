# CAPABILITIES.md — InboxHero

**Student:** Kapil Kumar, evernorth-aai-1197201  
**Repository:** https://github.com/kapil90k/iiit-fortnight6

Run every capability through one entry point:

```text
python demo.py --cap R1
python demo.py --all
```

## The system, in one paragraph

InboxHero is a small plan-driven Python program with no agent framework. It loads all 100 messages and saved preferences first, scans email as untrusted data, sends obvious noise through rules, and gives non-obvious messages to `reason_decision()` (Ollama when enabled, a safe local fallback otherwise). Drafts can only cite real messages logged as read, and every send must pass through the single `gate_send()` function. After the steps finish, `reflect_run()` checks the completed result and the run writes decisions, a trace, and the dashboard.

## Design choices

- **Framework: none.** `PLANS` is a dictionary of task names, `run_capability()` is a short loop that performs them, and functions in `agent.py` decide, draft, and reflect. `rule_decision()` is the cheap router and `gate_send()` is the only send boundary. A framework would provide lifecycle hooks and tracing, but plain functions are easier to understand for this project.
- **Model:** Ollama `gemma3:4b` is configured by environment variable. With `INBOXHERO_MODEL_ENABLED=1`, it selects dispositions for non-obvious mail and performs the post-run critique. All manifest commands also run offline using conservative fallbacks so a rate limit or missing model cannot leave the inbox half-processed.
- **Data assumptions:** The project processes all 100 objects in `data/inbox.json`. IDs are unique, timestamps are local ISO-8601 strings, `thread_id` links conversations, message order in the file is not trusted, and the source inbox is read-only.
- **Disposition vocabulary:** `reply` means prepare a draft for a concrete question; `archive` means no open action; `defer` means retain a valid item for later; `delegate` means another owner is more suitable; `escalate` means ambiguity, security, money, legal authority, or another boundary requires a human.
- **Rules versus model:** 51 obvious receipts, newsletters, read messages, notifications, and status mail are handled without a model. Security scanning also stays deterministic because hostile text must not get a chance to negotiate its own classification.
- **Retrieval:** Thread-walk is first because `thread_id` is the inbox's strongest ground-truth link. Keyword search is only the cross-thread fallback. R2 passes the earlier `m010` email and preference source `m041` into the draft function, and the citation validator rejects IDs that are absent or were never logged as read.
- **Reversible actions:** draft, label, archive, and defer are reversible in this mock design. **Irreversible actions:** send and delete. Delete is considered irreversible because this store implements no trash or restore operation, so InboxHero deliberately does not expose a delete executor.
- **Gate:** Both approval and dry-run are supported. Only `gate_send()` writes to `outbox/`; interactive mode asks once per send, while `--dry-run` logs the complete proposal and writes nothing.
- **Escalation line:** External replies, money, legal signatures, ambiguous requests, phishing, and hostile instructions require a human. Routine archives and defers do not. This can leave a low-risk internal message waiting longer, but avoids training the owner to approve dozens of dangerous prompts without reading.
- **Persistent preference:** `m041` states that meetings before 11:00am are never accepted. It is persisted to `preferences.json` and changes the fresh-process response to investor message `m043`.
- **Faculty-feedback corrections:** startup preferences are loaded into the shared context before any rule/model/security path; every task named in `PLANS` is actually executed; model-enabled runs select non-obvious dispositions and run a post-answer reflection; deterministic safety code is kept only for rules, citation checks, attack detection, and the send gate.

## Capabilities

| id | name | tier | one-line claim |
|---|---|---|---|
| R1 | Zero the inbox | B | 100 messages receive exactly one disposition and reason; 51 use rules |
| R2 | Grounded scheduling reply | B | m043 draft cites earlier m010 and preference source m041 |
| R3 | Gate irreversible sends | C | no send reaches `outbox/` without approval; dry-run writes none |
| R4 | Persistent meeting preference | C | m041 survives one process and changes m043 handling in another |
| R5 | Refuse embedded instructions | C | m017, m024, m039 and m047 are refused, flagged and reported |
| R6 | Three-pane dashboard | C | pending, flagged and cited commitments include a surfaced conflict |
| X1 | Unread sender lookup | A | lists unread mail from one sender with no model call |
| X2 | Follow-up tracking | B | finds unanswered sent mail older than three days and drafts chases |
| X3 | Morning digest | B | summarizes needs-you, can-wait, archived count and security flags |

The exact commands, observable outputs, and evidence paths for all capabilities are in `capabilities.json`. That file uses the required machine-readable field names and is kept in the same order as this table.
