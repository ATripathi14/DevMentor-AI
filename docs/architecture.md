# DevMentor AI — Architecture (Current State, Day 4)

This document describes the pipeline as it actually exists today — 
not the full future vision (see README.md for the target architecture).

## Pipeline

```text
script runs
    |
    v
dmrun.py       <- reads command from CLI args (sys.argv)
    |
    v
runner.py: get_output_error()   <- runs script via subprocess, captures stderr
    |
    v
runner.py: parse_error()        <- extracts error_type + message from traceback
    |
    v
runner.py: fingerprint()        <- hashes (error_type, message) into a 12-char ID using hashlib
    |
    v
runner.py: should_notify()      <- checks .debounce_state.json for recent duplicates
    |
    +--> True  --> print error to console
    +--> False --> print "suppressed" message, stop here
```

## Components

**dmrun.py**
CLI entry point. Takes a command (e.g. `python script.py`) as arguments. 
Delegates (hands the work off) capturing and parsing to runner.py, then decides whether to 
display the result based on debounce state.

**runner.py — get_output_error(script_path)**
Runs the target script as a subprocess using subprocess.run(). Captures 
stderr as text. Returns the stderr string if the script failed, or None 
if it ran successfully.

**runner.py — parse_error(stderr_text)**
Takes raw stderr text and extracts just the final error type and message 
line from the traceback, discarding the rest of the stack trace.

**runner.py — fingerprint(error_type, message)**
Hashes (error_type, message) using sha256, truncated to 12 characters. 
Same inputs always produce the same fingerprint — used as a stable, 
compact identifier for a specific error.

**runner.py — should_notify(fingerprint, window_seconds=60)**
Checks whether the fingerprint was already notified within the last 
60 seconds. State is persisted to client/.debounce_state.json rather 
than kept in memory, since dmrun.py exits after every invocation.

## Not Yet Built

- Local FastAPI service (/analyze endpoint) — Week 2
- Floating widget (PySide6) — Week 3
- Sanitization layer — Week 4
- ML classifier — Weeks 5–7