# DevMentor AI — Architecture (Current State)

This document describes the pipeline as it actually exists today — 
not the full future vision (see README.md for the target architecture).

## Pipeline

```text
script runs
    |
    v
dmrun.py    <- reads command from CLI args (sys.argv)
    |
    v
runner.py: get_output_error()   <- runs script via subprocess, captures stderr
    |
    v
runner.py: parse_error()     <- extracts error_type + message from traceback
    |
    v
sanitizer.py: sanitize()     <- redacts paths, emails, tokens, env var
    |                               values, and URL credentials from message
    v
sanitizer.py: assess_risk()     <- re-scans sanitized text for anything
    |                               still suspicious
    |
    +--> "review" --> print raw error + review notice, stop here (fail closed)
    |
    +--> "safe"
         |
         v
    runner.py: fingerprint()     <- hashes (error_type, SANITIZED message)
         |                              into a 12-char ID using hashlib
         v
    runner.py: should_notify()      <- checks .debounce_state.json for
         |                              recent duplicates
         |
         +--> False --> print "suppressed" message, stop here
         |
         +--> True
              |
              v
         dmrun.py: POST /analyze     <- sends error_type, SANITIZED message,
              |                          fingerprint to local FastAPI service
              |
              +--> server unreachable --> print raw error + "start the service" message
              |
              v
         local_service/main.py: analyze()
              |
              v
         explainer.py: normalize_error_type()     <- maps raw exception name
              |                                      to one of 12 category labels
              v
         explainer.py: EXPLANATIONS       <- looks up plain-English
              |                              explanation for that category
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
Delegates capturing and parsing to runner.py, sanitizes the message, 
checks its risk level, then decides whether to display the result 
based on debounce state. If not suppressed, POSTs the sanitized error 
to the local FastAPI service and prints the returned explanation.

**runner.py — get_output_error(script_path)**
Runs the target script as a subprocess. Captures stderr as text. 
Returns the stderr string if the script failed, or None if it succeeded.

**runner.py — parse_error(stderr_text)**
Extracts the error type and message from the final traceback line.

**sanitizer.py — sanitize(text)**
Chains all 5 sanitizers in sequence: URLs first, then emails, tokens, 
env vars, and paths last. Order is deliberate — URLs must be sanitized 
before paths, since the path pattern's collision-avoidance for `//` 
only works correctly on text that hasn't already been partially altered.

**sanitizer.py — sanitize_paths / sanitize_emails / sanitize_tokens / 
sanitize_env_vars / sanitize_urls**
Each redacts one category of sensitive data (file paths, email 
addresses, long tokens/API keys, environment variable values, and 
URL-embedded credentials respectively), replacing matches with a 
labeled placeholder like [REDACTED_PATH].

**sanitizer.py — assess_risk(sanitized_text)**
A second, stricter safety check run after sanitization. Scans for any 
remaining long alphanumeric run (16+ characters, a lower threshold 
than sanitize_tokens' 20) that might indicate something slipped 
through. Returns "review" (blocks the POST, fails closed) or "safe".

**runner.py — fingerprint(error_type, message)**
Hashes (error_type, message) using sha256. Runs on the SANITIZED 
message, not the raw one — this way the fingerprint reflects the 
meaningful error content, not incidental sensitive details, and 
guarantees no sensitive data reaches the fingerprint or debounce state.

**runner.py — should_notify(fingerprint, window_seconds=60)**
Checks whether this specific fingerprint was seen within the last 60 
seconds, independently per fingerprint. Persisted to 
client/.debounce_state.json, since dmrun.py exits after every invocation.

**local_service/settings.py — load_settings() / save_settings()**
Reads/writes local_service/settings.json. Defaults to 
{privacy_mode: "local_only", confidence_threshold: 0.6}. Auto-creates 
the file with defaults on first use. Not yet wired into the analyze 
pipeline — currently just a standalone settings store, in preparation 
for future privacy-mode switching.

**local_service/main.py — GET / / POST /analyze / GET /latest**
Health check, error categorization + explanation lookup (receiving the 
already-sanitized message), and most-recent-result polling endpoint, 
respectively.

**local_service/explainer.py — normalize_error_type / EXPLANATIONS**
Maps raw exception names to 12 category labels, and looks up a 
plain-English explanation for each category.

**client/widget.py — DevMentorWidget**
A PySide6 always-on-top floating window. Polls GET /latest every 2 
seconds, updates only when the fingerprint changes. Includes Dismiss, 
Copy (with "Copied!" confirmation), and a system tray icon with 
show/hide toggle and Exit.

## Known Gaps and Limitations

- none_type_error is currently unreachable: NoneType errors surface as 
  TypeError or AttributeError with "NoneType" in the message text, not 
  as their own exception class. To be fixed during dataset work.
- Unix paths containing spaces are only partially redacted. Accepted 
  as a low-risk limitation rather than adding regex complexity.
- Windows paths using forward slashes leave the bare drive letter 
  visible. Minor, accepted limitation.
- settings.py exists but isn't yet wired into main.py's actual 
  request-handling logic — privacy_mode has no effect yet.

## Not Yet Built

- ML classifier — 
- Cloud-assisted explanation modes (Sanitized Cloud / Advanced Cloud)