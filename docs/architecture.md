# DevMentor AI — Architecture (Current State, Week 3 Day 5)

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
    +--> False --> print "suppressed" message, stop here
    |
    +--> True
         |
         v
    dmrun.py: POST /analyze     <- sends error_type, message, fingerprint
         |                         to local FastAPI service (localhost:8765)
         |
         +--> server unreachable --> print raw error + "start the service" message
         |
         v
    local_service/main.py: analyze()
         |
         v
    explainer.py: normalize_error_type()  <- maps raw exception name
         |                                    (e.g. "KeyError") to one of
         |                                    12 category labels
         v
    explainer.py: EXPLANATIONS            <- looks up plain-English
         |                                    explanation for that category
         v
    stores result (incl. fingerprint) in latest_result (in-memory)
         |
         v
    returns {explanation, category, source, fingerprint} to dmrun.py
         |
         v
    dmrun.py prints: [category] explanation
         |
         |    (meanwhile, independently, every 2 seconds:)
         |
         v
    widget.py: QTimer polls GET /latest
         |
         v
    compares fingerprint to last one shown
         |
         +--> unchanged --> do nothing
         |
         +--> new --> update floating widget label with [category] explanation
```

## Components

**dmrun.py**
CLI entry point. Takes a command (e.g. `python script.py`) as arguments. 
Delegates (hands the work off) capturing and parsing to runner.py, then 
decides whether to display the result based on debounce state. If not 
suppressed, POSTs the error to the local FastAPI service and prints the 
returned explanation. If the service is unreachable, falls back to 
printing the raw error with a message telling the user how to start it.

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
Checks whether this specific fingerprint was already notified within 
the last 60 seconds. Tracks each fingerprint's own timer independently — 
an unrelated error occurring in between does not reset another 
fingerprint's suppression window. State is persisted to 
client/.debounce_state.json rather than kept in memory, since dmrun.py 
exits after every invocation.

**local_service/main.py — GET /**
Basic health-check route confirming the server is running.

**local_service/main.py — POST /analyze**
Receives {error_type, message, fingerprint} (validated automatically 
by Pydantic — malformed requests are rejected with a 422 error before 
this code runs). Normalizes the error type to a category, looks up its 
explanation, stores the result (including the fingerprint) as the 
latest, and returns it.

**local_service/main.py — GET /latest**
Returns the most recently analyzed result, or a placeholder message if 
nothing has been analyzed yet since the server started. Result (incl. 
fingerprint) is kept in an in-memory dictionary, since the server is a 
long-running process, unlike dmrun.py.

**local_service/explainer.py — normalize_error_type(raw_error_type)**
Maps a raw Python exception class name (e.g. "KeyError", 
"requests.exceptions.ConnectionError") to one of the 12 official 
category labels. Falls back to "other_error" for anything unrecognized.

**local_service/explainer.py — EXPLANATIONS**
Dictionary mapping each of the 12 category labels to a plain-English 
explanation and suggested fix.

**client/widget.py — DevMentorWidget**
A PySide6 always-on-top floating window. Polls GET /latest every 2 
seconds via a QTimer; compares the returned fingerprint to the last one 
displayed, and only updates the label when it's genuinely new — this 
runs completely independently of dmrun.py, so the widget reacts to any 
error analyzed by the service, regardless of what triggered it. Includes 
Dismiss (hides, doesn't close), Copy (copies the current explanation to 
the clipboard, with brief "Copied!" confirmation), and a system tray 
icon with a right-click menu (Show Widget / Exit) plus single-click 
toggle for showing/hiding.

## Issues yet to resolve

- none_type_error is currently unreachable: NoneType errors surface as 
  TypeError or AttributeError with "NoneType" in the message text, not 
  as their own exception class. normalize_error_type() only checks 
  exception names right now. To be fixed during dataset work.

## Not Yet Built

- Sanitization layer 
- ML classifier 