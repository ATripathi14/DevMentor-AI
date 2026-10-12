# DevMentor AI — Architecture (Current State, v0.5)

This document describes the pipeline as it actually exists today — 
not the full future vision (see README.md for the target architecture).

## Pipeline

```text
script runs
    |
    v
dmrun.py                           <- reads command from CLI args (sys.argv)
    |
    v
runner.py: get_output_error()      <- runs script via subprocess, captures stderr
    |
    v
runner.py: parse_error()           <- extracts error_type + message from traceback
    |
    v
sanitizer.py: sanitize()           <- redacts paths, emails, tokens, env values,
    |                              URL credentials, memory addresses
    v
sanitizer.py: assess_risk()        <- re-scans sanitized text for anything
    |                               still suspicious
    |
    +--> "review" --> print raw error + review notice, stop here (fail closed)
    |
    +--> "safe"
         |
         v
    runner.py: fingerprint()       <- hashes (error_type, SANITIZED message)
         |                          into a 12-char ID using hashlib
         v
runner.py: should_notify()         <- checks .debounce_state.json for
         |                             recent duplicates
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
         classifier_service.py: predict()   <- calibrated Linear SVM on
              |                                "{error_type} {message}",
              |                                returns category + confidence
              v
         confidence >= threshold (settings.json, 0.6)?
              |
              +--> yes --> use ML category        (source: "ml")
              |
              +--> no  --> explainer.py: normalize_error_type()
              |            rules mapping          (source: "rules")
              v
         explainer.py: EXPLANATIONS   <- plain-English explanation for category
              |
              v
         stores result in latest_result (in-memory)
              |
              v
         returns {explanation, category, source, confidence, fingerprint}
              |
              v
         dmrun.py prints: [category] explanation
              |
              |    (meanwhile, independently, every 2 seconds:)
              |
              v
         widget.py: background QThread polls GET /latest
              |
              v
         compares fingerprint to last one shown
              |
              +--> unchanged --> do nothing
              |
              +--> new --> widget shows "[category] · high/medium/low
                           confidence (NN%)" or "· pattern-matched",
                           then the explanation
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
Chains 6 sanitizers in order: URLs, object memory addresses, emails,
tokens, env vars, paths. Order is deliberate: URLs must run before paths,
since the path pattern's `//` protection only works on unaltered text.

**sanitizer.py — sanitize_paths / sanitize_emails / sanitize_tokens / 
sanitize_env_vars / sanitize_urls / sanitize_object_addresses**
Each redacts one category of sensitive data (file paths, email 
addresses, long tokens/API keys, environment variable values, 
URL-embedded credentials, and object memory addresses), replacing 
matches with a labeled placeholder like [REDACTED_PATH].
sanitize_object_addresses redacts Python object addresses 
(e.g. 0x1bda620db90) as [REDACTED_ADDRESS]. They change on every run, 
which made the dataset non-reproducible.

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
Reads/writes settings.json (defaults: privacy_mode "local_only",
confidence_threshold 0.6). `confidence_threshold` is used by /analyze for
ML-versus-rules routing. `privacy_mode` is stored but has no effect yet.

**local_service/main.py — GET / , POST /analyze , GET /latest**
/analyze runs the ML classifier first and falls back to the rules mapping
below the confidence threshold. The response includes category, source
("ml" or "rules"), confidence and fingerprint. /latest returns the most
recent result.

**local_service/classifier_service.py — predict(error_type, message)**
Loads classifier.joblib and vectorizer.joblib once at import. Builds
"{error_type} {message}", vectorizes it, and returns the top category with
its calibrated probability.

**local_service/explainer.py — normalize_error_type / EXPLANATIONS**
Maps raw exception names to 12 category labels, and looks up a 
plain-English explanation for each category.

**ml_engine/train.py and dataset.csv**
train.py rebuilds the saved model from the 132-row labelled dataset: TF-IDF
(1-2 grams) plus Linear SVM wrapped in CalibratedClassifierCV (cv=2).
The notebook ml_engine/notebooks/training_and_evaluation.ipynb is the
authoritative record. Macro F1 is 0.931 under 3-fold CV.

**client/widget.py — DevMentorWidget**
PySide6 always-on-top floating window. A background QThread polls /latest
every 2 seconds, so network calls never block the UI. Shows a header with
the category and confidence band or "pattern-matched", then the
explanation. Features: Copy ("Copied!" feedback), Dismiss, collapse/expand,
light/dark theme, drag to move, Escape to hide, tray icon (click to toggle,
menu with Show/Hide/Exit), and auto-resurface when a new error arrives.
No global keyboard hooks; keys are handled only while the widget has focus.

## Known Gaps and Limitations

- NoneType errors share message templates with attribute_error and
  type_error. The ML model handles most cases, but none_type_error remains
  the weakest category (about 0.50 F1 on the single split). The rules path
  cannot distinguish them at all, since it sees only the exception name.
- Unix paths containing spaces are only partially redacted. Accepted 
  as a low-risk limitation rather than adding regex complexity.
- Windows paths using forward slashes leave the bare drive letter 
  visible. Minor, accepted limitation.
- Evaluation is on 132 generated messages, not real-world tracebacks, so
  real accuracy is likely lower. A real dataset is planned for v2.
- settings.json's privacy_mode is stored but not yet acted on.

## Yet to be Built

- Local LLM mode (Ollama), in progress for v1.0
- Cloud-assisted explanation modes (Sanitized Cloud / Advanced Cloud)
- v2: real-world traceback dataset and multi-language support