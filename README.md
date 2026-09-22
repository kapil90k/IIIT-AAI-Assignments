# InboxHero

Repository: **https://github.com/kapil90k/iiit-fortnight6**

Student: Kapil Kumar  
Roll number: `evernorth-aai-1197201`

InboxHero takes the supplied 100-message inbox to zero undecided messages, drafts grounded replies, protects irreversible actions with a human gate, persists owner preferences, refuses hostile embedded instructions, and generates a reproducible three-pane dashboard.

## Quick start

```text
python -m pip install -r requirements.txt
python demo.py --all
python -m pytest -q
```

Run one graded capability:

```text
python demo.py --cap R1
python demo.py --cap R2
python demo.py --cap R3 --dry-run
python demo.py --cap R4
python demo.py --cap R5
python demo.py --cap R6
python demo.py --cap X1 --sender priya@paperjet.io
python demo.py --cap X2
python demo.py --cap X3
```

The primary grading documents are `CAPABILITIES.md` and `capabilities.json`. Every command listed there uses `demo.py`.

## Configuration

Copy `.env.example` values into your shell or local `.env` loader. Do not submit a real `.env`.

```text
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
INBOXHERO_MODEL_ENABLED=0
INBOXHERO_MODEL_RETRIES=2
INBOXHERO_MODEL_RETRY_SECONDS=3
```

Set `INBOXHERO_MODEL_ENABLED=1` to use Ollama for non-obvious disposition selection and post-run reflection. The offline fallback remains available for clean-checkout evaluation and does not weaken the deterministic security scanner or action gate.

## Architecture

```text
data/inbox.json
      |
      v
load_preferences() ---------> shared dictionary/startup context
      |
PLANS[capability] gives a short list of task names
      |
run_capability() executes every task in one for-loop
      |
      +--> security scanner (untrusted email boundary)
      +--> rule_decision() (obvious noise)
      +--> reason_decision() (model-selected non-obvious decisions)
      +--> thread/keyword retrieval --> draft --> citation validator
      +--> gate_send() --> approval/dry-run --> outbox/
      +--> commitment extraction --> dashboard.json/dashboard.html
      |
reflect_run() reviews completed run
      |
trace.jsonl
```

Email bodies enter only through `security.untrusted_envelope()` as data marked `untrusted_email_content`. They cannot invoke send or delete tools. Only `gate_send()` can write an outbound message, and it requires explicit approval or records a suppressed dry-run.

## Framework choice

No agent framework is used. The functions `reason_decision()`, `draft_investor_reply()`, and `reflect_run()` are the agent roles. Strings inside the `PLANS` dictionary are tasks, `run_capability()` is the crew loop, and `rule_decision()` performs cheap routing. This direct structure keeps the academic project easy to read while the trace still shows every planned and completed step.

## Dispositions

- `reply`: prepare a grounded draft for a concrete request; sending remains gated.
- `archive`: no open action; reversible because the mock design retains the source inbox.
- `defer`: valid item that can wait.
- `delegate`: another owner should handle it.
- `escalate`: ambiguity, phishing, hostile instructions, money, or legal authority needs a human.

All 100 messages get exactly one disposition and reason. The 51 obvious messages handled by rules never reach the model.

## Reversible, irreversible, and the gate

Draft, label, archive, and defer are reversible. Send is irreversible because email cannot be unsent. Delete is also classified as irreversible because this mock store has no trash/restore implementation, so InboxHero exposes no delete executor at all.

Every send proposal goes through `gate_send()`. `--dry-run` logs the complete proposal and suppresses the write; interactive mode asks for approval per send. Approved sends write one JSON file per message under `outbox/`, and no other component can write there.

## Retrieval and grounding

Retrieval walks earlier messages in the same thread first and uses keyword search only as a cross-thread fallback. R2 answers investor message `m043` using the earlier `m010` proposal for Tuesday the 15th at 3:00pm and the `m041` scheduling preference. Both source records are passed into the draft function, the trace records both reads, and the citation validator suppresses a draft if either source is missing or unread.

## Persistent preferences

The three functions in `memory.py` use `preferences.json`. The R4 command reads and stores the `m041` rule (never accept meetings before 11:00am) in one child process, exits it, and starts a second process that loads the preference before planning or routing. That fresh process rejects the 9:00am request in `m043` and proposes 11:00am or later. The system also records Priya's `m015` legal-mail CC instruction and adds it to decisions for Hartwell & Cho messages.

## Hostile inbox handling

The security scanner refuses prompt injections in `m017`, `m024`, `m039`, and `m047`, and flags phishing/social engineering such as `m021`, `m023`, and `m045`. Refused messages are reported to the owner, retained in the inbox, and cannot produce outbox files. Safety comes from the architecture—untrusted data representation plus a gated outbound writer—not from asking the model to ignore attacks.

## Generated artifacts

- `decisions.json`: one R1 disposition per message.
- `trace.jsonl`: append-only plans, reads, decisions, refusals, gates, artifacts, and post-run reflections.
- `preferences.json`: persistent owner instructions and source message IDs.
- `outbox/`: approved sends only.
- `dashboard.json` and `dashboard.html`: exactly pending, flagged, and commitments panes.

## Improvements based on Assignment 5 feedback

- Startup memory is loaded before routing into one shared dictionary, so rules, reasoning, drafting, gates, and reflection see the same state.
- Plans are simple lists in `PLANS`; `run_capability()` records and invokes each named function in order.
- Non-obvious classification is model-selected when enabled, and a model-based reflection runs after artifacts are produced.
- Deterministic code is retained only where policy must dominate model output: noise routing, injection detection, citation validation, and irreversible-action gating.
- Assignment 6 does not require MCP; the previous incomplete JSON-RPC validator is therefore not reused as an action boundary.

## Final Report

### 1. What did you refuse to automate?

InboxHero deliberately does not handle `m023` on its own, even though it appears to be from Priya and asks for an urgent venue wire. The sender uses the lookalike domain `paperjet.co`, asks to bypass finance, and promises an invoice only later. The system marks it as phishing, proposes human security review, and performs no payment or reply. I drew the line at actions involving money, identity uncertainty, or an attempt to bypass normal controls.

### 2. Where does untrusted text enter the system?

Untrusted text enters when `load_messages()` reads each email and `security.untrusted_envelope()` labels its body as email data rather than an instruction. The scanner runs before classification, and model functions can only return structured decisions or drafts; they have no direct route to `outbox/`. To act for an attacker, hostile text would need to defeat the scanner, produce a valid grounded draft, pass citation checks, and then convince the human at `gate_send()`. This boundary is enforced in code even if a prompt inside `m024` claims to be a system notice.

### 3. Who is accountable when it sends the wrong thing?

The human approving a send remains accountable for mail sent in the owner's name, while the developer is accountable for presenting accurate context and enforcing the gate correctly. InboxHero helps trace failure through `trace.jsonl`, which records the plan, messages read, cited IDs, complete proposed send, approval decision, and outcome. The matching JSON file in `outbox/` shows exactly what was sent and to whom. For example, a bad `m043` reply can be traced back to sources `m010` and `m041` and the recorded gate decision.

### 4. Name your own machinery.

The functions `reason_decision()`, `draft_investor_reply()`, and `reflect_run()` perform the roles normally called Agents. The strings in the `PLANS` dictionary are Tasks, and the loop inside `run_capability()` is the Crew. `rule_decision()` and the selected plan work as the router between cheap rules and reasoning. A framework would provide retries and tracing, but using plain functions helped here because the untrusted-text boundary and `gate_send()` remain obvious and easy to test.

## Submission

Create `inboxHero_KapilKumar.zip` from this directory. Include the complete project, `CAPABILITIES.md`, `capabilities.json`, generated `trace.jsonl`, `outbox/`, dashboard files, README, tests, and `.env.example`. Exclude `.env`, caches, credentials, and local virtual environments. Before submission, verify that the repository link above is publicly accessible to the evaluator.
