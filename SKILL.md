---
name: agent-detention-protocol
description: Enforce repeated-failure remediation across governed agents.
version: 0.1.0
author: Erin Tiffany, Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [governance, remediation, reliability, multi-agent]
    related_skills: []
---

# Agent Detention Protocol

This is a mechanical reliability state machine, not a moral judgment or emotional punishment. It tracks established, actionable requirements by capacity; three materially identical eligible failures in a row open Detention; ordinary work then pauses. Before practice begins, the agent must complete a structured failure investigation. It is then required to complete 100 consecutive successful repetitions by default, followed by competency-gated release. “Writing sentences” is metaphorical: the required unit is a structured explanation, corrected procedure, constrained practice, and observable demonstration.

## When to Use

Use for every governed agent and every task where an established instruction or capability can be evaluated. Use the protocol before ordinary work, after every evaluated result, when opening or releasing Detention, and for monthly training assignment.

Do not count external outages, ambiguous requirements, changed direction, insufficient information, legitimate unknowns, or unrelated technical failures as instruction noncompliance.

## Enforcement model

The protocol has two layers:

1. **Deterministic state engine:** `detention_protocol.py` owns counters, transitions, persistence, and release gates. The model must not edit its state file directly.
2. **Agent adapter:** every agent surface must call `status` before ordinary work and call `failure` or `success` after each evaluated attempt. A Detention response is a hard stop: do not perform a fourth ordinary attempt.

The shared state path is controlled by `CYPHER_DETENTION_STATE`; if unset, the engine uses `~/.hermes/agent-detention/state.json`. A host integration may set the variable to a governed MIND_box or organization-wide state location.

## State machine

```text
NORMAL → failure 1 → failure 2 → identical failure 3 → DETENTION
DETENTION → corrective practice quota + competency PASS → RELEASED → NORMAL
```

Counters are keyed by `(capacity, requirement)`, not globally. Any valid success for that exact key resets its consecutive counter while preserving history.

## Procedure

1. Resolve the agent identity, capacity, requirement, expected result, and evaluation criteria before acting.
2. Run `status <agent>` through `terminal` using the protocol script. If state is `DETENTION`, stop ordinary work and perform only the active remediation.
3. After an eligible failure, run `failure <agent> <capacity> <requirement> <expected> <observed> --evidence ...`. Classify eligibility from evidence, never from presumed motive.
4. If the result reports `detention_triggered: true`, pause the task immediately and preserve the returned detention ID.
5. Complete the investigation before practice. Preserve the original assignment, the failed response, and a separate accurate response showing what should have been done. Then record the exact failure, how it happened, why it happened, contributing causes, prevention controls, and an observable behavior classification such as `ignored`, `overwrote`, `deleted`, `omitted`, or `unknown`. Do not claim private intent from behavior alone.
6. After investigation, perform 100 consecutive successful practice units by default using `practice <agent> <detention_id> PASS|FAIL --evidence ...`. A failed practice unit resets the consecutive success count. Each unit must include a corrected plan or tool sequence, constrained exercise result, and evidence.
7. Call `release` only after the required practice quota passes. A release attempt without investigation or competency PASS must fail closed.
8. After a valid success, call `success` to reset the exact consecutive-failure counter.
9. At the monthly boundary, call `monthly <agent> YYYY-MM` to assign failure-based training or record free choice when no Detention occurred.

## Commands

Use the shared script through `terminal`:

```text
python3 detention_protocol.py status AGENT
python3 detention_protocol.py failure AGENT CAPACITY REQUIREMENT EXPECTED OBSERVED --evidence EVIDENCE
python3 detention_protocol.py success AGENT CAPACITY REQUIREMENT --evidence EVIDENCE
python3 detention_protocol.py investigate AGENT DET-0001 ASSIGNMENT FAILED_RESPONSE ACCURATE_RESPONSE EXACT_FAILURE HOW_FAILED WHY_FAILED CAUSES PREVENTION BEHAVIOR_CLASSIFICATION
python3 detention_protocol.py practice AGENT DET-0001 PASS --evidence EVIDENCE
python3 detention_protocol.py release AGENT DET-0001
python3 detention_protocol.py monthly AGENT 2026-10 --choice SUBJECT
```

## Universal integration contract

Adapters for Hermes profiles, delegated workers, external CLIs, and API agents must implement these hooks:

- `before_action(agent, task, requirement)`: read state; deny ordinary work during Detention.
- `after_result(agent, requirement, expected, observed, evidence)`: classify and record success/failure.
- `on_detention(agent, detention_id)`: interrupt the current work loop and begin remediation.
- `on_release(agent, detention_id)`: require a passed competency result before resuming.

A skill or agent that bypasses these hooks is not governed by this protocol; universal enforcement requires routing all agent entry points through an adapter or wrapper.

## Verification

A valid installation must demonstrate:

- failures are isolated by capacity and requirement;
- unrelated failures do not combine;
- three identical eligible failures open Detention;
- external/ambiguous failures do not increment the counter;
- ordinary work is blocked while Detention is active;
- release fails before the practice quota passes;
- release succeeds only after competency PASS;
- monthly training is assigned after Detention and elective without Detention;
- state writes are atomic and preserve the full event history.

## Limitations

A prompt-only skill cannot technically prevent a separately launched, unwrapped agent from acting. The deterministic engine and adapters provide enforceability only when every agent entry point is routed through them. External agents outside Hermes require their own adapter or a gateway wrapper.
