# Final Report Answers (Assignment 04)

## 1) Retrieval grounding vs function-call grounding risk profile
In retrieval grounding, the main risk is factual mismatch: the model may retrieve the wrong chunk or miss context. In function-call grounding, the risk expands to operational risk because a bad call can trigger wrong workflows and time-sensitive decisions. A retrieval mistake usually creates a bad explanation, while a function-call mistake can produce bad action recommendations or stale state-dependent conclusions. This is why tool systems require stronger guardrails, validation, and observability.

## 2) Schema-function drift impact and detection
If function signatures and tool schemas drift, the model will call parameters that the function does not accept, causing runtime argument errors. In this project, those errors are surfaced through structured error responses from the tool executor, which prevents crashes but still harms answer quality. The best prevention is contract testing that compares schema parameters to Python signatures. CI should run these tests so drift is caught before deployment.

## 3) Risk change for mutating tools and required safeguard
Read-only tools are relatively safer because they fetch state; mutating tools (cancel booking or reassign gate) can create irreversible operational impact. If the model chooses the wrong target or arguments, the side effect is immediate and costly. A required safeguard is human-in-the-loop confirmation with explicit summary of intended action and identifiers before execution. Role-based authorization and idempotency tokens should also be mandatory.

## 4) What mattered more: function descriptions or system prompt
Function descriptions mattered more for precise tool selection in most tests. When descriptions clearly stated when to use a tool and what it returns, wrong tool choices reduced significantly. The system prompt helped enforce behavior and format, but it could not fully recover from vague or overlapping tool descriptions. In short, good tool semantics drove better selection, while prompts improved consistency.

