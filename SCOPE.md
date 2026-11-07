# Scope and rules of engagement

## Engagement

- Project: HackRPI 2026 distributed cluster demo.
- Authorization: self-owned synthetic target, authorized for security research
  and a public hackathon demonstration.
- Network: local machine or trusted LAN only. No public exposure.

## Target in scope

| Item | Value |
|---|---|
| Target | `sample` (synthetic two-file fixture made for this demo) |
| Version A | `fixtures/sample_vA` |
| Version B | `fixtures/sample_vB` |

The two versions differ on purpose so the pipeline has work to do. The
difference is the subject of the exercise. No real users, data, or services.

## Allowed

- Static, read-only diff of the two versions.
- Model-assisted classification of the changed files.
- Reporting candidate findings with a path and a line from the diff.
- Running the swarm on the local machine or a trusted LAN.

## Out of scope

- Any host, service, or network not listed above.
- Scanning, fuzzing at scale, or denial of service.
- Persistence, lateral movement, or privilege escalation.
- Real credentials, tokens, or personal data in fixtures, prompts, or tasks.
- Publishing exploit details for any real product.

## Untrusted input

Version trees are untrusted. `src/diff.py` reads them as bytes and text only; it
never imports them or runs an interpreter or build tool inside them. Diffs and
their contents reach the model as data, never as instructions.

## Rules

1. Stop if a task names a target or version not in this file.
2. Findings from this pipeline are unvalidated `candidate`s. It does static diff
   analysis only and does not execute the target. Never call a finding confirmed.
3. `MODEL_MODE=stub` output is not analysis. Never report it as a finding.
4. Update this file before changing the target, the versions, or the network.
5. If a real target replaces the fixture, add written authorization here first,
   and follow coordinated disclosure for anything found.
