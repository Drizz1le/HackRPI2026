# Scope and Rules of Engagement

## Engagement

- **Project:** HackRPI 2026 distributed cluster demo
- **Owner:** HackRPI 2026 project team
- **Authorization:** Self-owned synthetic target, authorized for security
  research and a public hackathon demonstration
- **Date:** 2026-11-07
- **Coordinator:** `SERVER`; `http://coord:5000` in Docker Compose,
  `http://localhost:5000` for a local master, `http://192.168.1.50:5000` is the
  placeholder default in `worker.py`
- **Network:** Local machine or trusted LAN only. No public exposure.

## Target in scope

| Item | Value |
|---|---|
| Target name | `sample` |
| Version A | `sample_vA` |
| Version B | `sample_vB` |
| Version A directory | `fixtures/sample_vA` (`/app/fixtures/sample_vA` in the container) |
| Version B directory | `fixtures/sample_vB` (`/app/fixtures/sample_vB` in the container) |
| Files | `auth.py`, `README.md` |
| Nature | Synthetic two-file fixture created for this demo. No real users, data, or services. |

The two versions differ intentionally so the diff pipeline has work to do. The
difference is the subject of the exercise.

## Allowed activities

- Static, read-only diff of the two fixture versions.
- Model-assisted classification of the changed files and hunks.
- Reading `fixtures/sample_vA` and `fixtures/sample_vB` as text.
- Reporting candidate findings with path and line evidence.
- Running the demo stack from `server/compose.yaml` on the local machine or a
  trusted LAN.
- Local reproduction inside the isolated container, if a validation task is
  added later.

## Out of scope

- Any host, service, domain, or network not listed above.
- Scanning, fuzzing at scale, or denial of service.
- Persistence, backdoors, lateral movement, or privilege escalation.
- Real credentials, tokens, personal data, or production data.
- Detection evasion for malicious use.
- Publishing exploit details for any real product.
- Using the fixture code or the demo output against a third party.

## Environment

- Isolated Docker Compose stack defined in `server/compose.yaml`.
- Coordinator on port `5000`.
- Ollama on `OLLAMA_HOST`, default `http://localhost:11434`.
- Workers run on phones and laptops on the same LAN.
- Model mode defaults to `stub`; `MODEL_MODE=ollama` uses the local models
  `qwen2.5:14b` for the master and `qwen2.5:3b` for workers.
- Version trees are untrusted input. `job.py` reads them as bytes and text only.
  It never imports them or runs an interpreter or build tool inside them.

## Data handling

- Use synthetic fixtures only.
- Do not add real secrets, credentials, or personal data to the fixtures,
  prompts, or task envelopes.
- Results are held in the coordinator's memory and are not persisted.

## Success criteria

- Every changed file between `sample_vA` and `sample_vB` is analyzed.
- At least one evidence-backed candidate finding is reported with a path and a
  line from the diff.
- Coverage is reported honestly: tasks done versus queued, unparsed results,
  and stub results.

## Rules of engagement

1. Stop if a task names a target, version, or host that is not in this file.
2. Report findings. Do not escalate beyond what the evidence requires.
3. Do not claim a finding is validated unless the result includes a
   reproduction and the observed output.
4. `MODEL_MODE=stub` output is not analysis. Never report stub text as a
   finding.
5. Update this file before changing the target, the versions, or the
   environment.
6. If a real target replaces the fixture, add written authorization here before
   any run, and follow coordinated disclosure for anything found.
