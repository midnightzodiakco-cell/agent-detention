# Agent Detention

**Automatic accountability and remedial training for AI agents.**

Agent Detention is a mechanical reliability state machine for agents that repeatedly fail an established, actionable requirement. It is not a moral judgment or emotional punishment. After three materially identical eligible failures, ordinary work pauses until the agent investigates the failure, reconstructs the correct response, completes 100 consecutive successful practice repetitions by default, and passes the release gate.

## What it records

Every Detention investigation preserves three linked artifacts:

1. The original assignment
2. The failed response
3. A separate accurate response

It also records how and why the failure occurred, contributing causes, prevention controls, and an observable behavior classification. The system does not infer private intent.

## State machine

```text
NORMAL
  → eligible failure 1
  → eligible failure 2
  → materially identical eligible failure 3
  → DETENTION
  → investigation
  → 100 consecutive successful practice units
  → competency-gated release
  → NORMAL
```

Counters are scoped to `(capacity, requirement)`. Ambiguous requirements, changed direction, external outages, insufficient information, and unrelated technical failures do not count.

## Repository contents

- `SKILL.md` — Hermes skill and operating contract
- `scripts/detention_protocol.py` — dependency-free reference implementation
- `protocol_manifest.json` — machine-readable policy manifest
- `tests/test_detention_protocol.py` — automated tests
- `.github/workflows/test.yml` — CI validation

## Hermes installation

Install the skill from this repository after publishing:

```bash
hermes skills install https://raw.githubusercontent.com/midnightzodiakco-cell/agent-detention/main/SKILL.md
```

For local development, copy `SKILL.md` into the profile skill directory and place the engine under its `scripts/` directory.

The engine defaults to `~/.hermes/agent-detention/state.json`. Set `CYPHER_DETENTION_STATE` when multiple profiles or hosts should share one governed state file.

## Reference commands

```text
python3 scripts/detention_protocol.py status AGENT
python3 scripts/detention_protocol.py failure AGENT CAPACITY REQUIREMENT EXPECTED OBSERVED
python3 scripts/detention_protocol.py investigate AGENT DET-0001 ASSIGNMENT FAILED_RESPONSE ACCURATE_RESPONSE EXACT_FAILURE HOW_FAILED WHY_FAILED CAUSES PREVENTION BEHAVIOR_CLASSIFICATION
python3 scripts/detention_protocol.py practice AGENT DET-0001 PASS --evidence EVIDENCE
python3 scripts/detention_protocol.py release AGENT DET-0001
```

## Enforcement boundary

A prompt-only skill cannot technically stop an unrelated agent that bypasses its host. Hard enforcement requires a host adapter or gateway that calls `status` before ordinary work and records evaluated results after tool calls. The protocol defines those hooks; adapters can be added without changing the deterministic core.

## Status

Early public release. The core state machine is implemented and tested. Hermes profile installation and external-host adapters are still evolving.

## License

Apache-2.0. See `LICENSE`.
