# HackRPI 2026 — distributed diff vuln-hunting swarm

Run Qwen3.6-A3B on several computers on one LAN. The master splits a version
diff into one task per changed file, hands them out to workers, and each worker
runs the model on its task to find security-relevant change. The master collects
the results and synthesizes one report.

## Layout

```
start.bat          boots the local Qwen server, then the chosen role
nettest.bat        checks machine-to-machine reachability (no model needed)
src/master.py      coordinator + task splitter + synthesizer   (master only)
src/worker.py      pull task -> analyze diff -> post result     (every machine)
src/model.py       one local-Qwen call
src/diff.py        two versions -> one task per changed file
prompts/           worker.md, master.md  (the two system prompts)
fixtures/          synthetic demo target (sample_vA -> sample_vB)
SCOPE.md           authorization and rules of engagement
```

## Run

1. On the coordinator machine:
   ```
   start.bat -master
   ```
   It prints its IP, e.g. `Master IP: 192.168.1.23`.

2. On every other machine, pass that IP:
   ```
   start.bat 192.168.1.23
   ```

Each machine starts its own Qwen server (`llama-server` on `:8080`) using the
tuned flags in `start.bat`; edit the `LLAMA` / `BLOB` / `TEMPLATE` paths per
machine. The master also runs one local worker, so a single machine works end
to end. When every task has a result, the master prints the report and writes
`report.md`.

## Point it at a real target

```
set VERSION_A_DIR=C:\path\to\ios_vA
set VERSION_B_DIR=C:\path\to\ios_vB
set VERSION_A=16.5
set VERSION_B=16.6
start.bat -master
```

`VERSION_A_DIR` / `VERSION_B_DIR` can be two directories or two single files.
Update `SCOPE.md` before pointing at anything that is not the fixture.

## Test the network first

Campus and other locked-down wifi often isolate clients, so two laptops on the
same SSID still cannot reach each other. Check before the demo:

```
nettest.bat -serve        (master machine; prints its IP)
nettest.bat <master-ip>   (another machine; prints REACHABLE or BLOCKED)
```

`REACHABLE` means the swarm will work. `BLOCKED` means the network or a firewall
is in the way; see SCOPE and the fixes below.

## No model yet?

Wire up and test the whole pipeline with no model loaded:

```
set MODEL_MODE=stub
start.bat -master
```

Stub replies are never reported as findings.
