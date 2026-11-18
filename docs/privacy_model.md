# DevMentor AI — Privacy Model

This document describes exactly what data DevMentor AI collects, processes, and (if ever) transmits, and what it never touches at all.

## Current State

DevMentor AI operates entirely locally. No error data, sanitized or otherwise, is sent outside your own machine. All processing happens between processes on localhost: `dmrun.py`, the FastAPI service, and the floating widget. In `local_llm` mode this also includes a local Ollama process. The ML classifier is a pre-trained model loaded from disk, so classification needs no network access either.

The sanitizer is defence in depth now and prepares for optional cloud modes. `privacy_mode` in `settings.json` supports `local_only` (default) and `local_llm` (optional, see below). The cloud modes are planned.

## Local LLM Mode (optional)

When `privacy_mode` is `local_llm`, the category and sanitized error message are sent to a local Ollama process on localhost (port 11434), only for `other_error` or low-confidence (below 0.7) cases. The message is re-sanitized server-side before sending. Nothing leaves the machine. The default, `local_only`, makes no LLM calls. AI-generated text is labelled in the widget and marked "verify before applying". If Ollama is down or slow, the pre-written explanation is used with no error.

## What Gets Sanitized, and Why

Before an error message is fingerprinted, stored, or sent anywhere (even to the local service), it passes through `sanitize()`, which strips:

| Sensitive data type | Redacted as | Example |
|---|---|---|
| File paths (Windows & Unix) | [REDACTED_PATH] | C:\Users\name\file.py → [REDACTED_PATH] |
| Email addresses | [REDACTED_EMAIL] | john@example.com → [REDACTED_EMAIL] |
| Long tokens / API keys (20+ chars) | [REDACTED_TOKEN] | sk_live_51H8x... → [REDACTED_TOKEN] |
| Environment variable values | [REDACTED_VALUE] | SECRET_KEY=abc123 → SECRET_KEY=[REDACTED_VALUE] |
| Credentials embedded in URLs | [REDACTED_CREDENTIALS] | https://user:pass@host → https://[REDACTED_CREDENTIALS]@host |
| Python object memory addresses | [REDACTED_ADDRESS] | 0x1bda620db90 → [REDACTED_ADDRESS] |

Memory addresses are not strictly secret, but they are host-specific runtime detail and change on every run. Redacting them also keeps fingerprints and the training dataset reproducible.

## Data Handling Summary

Nothing leaves the device by default. Cloud modes are opt-in and planned for the future.

| Data | Can leave the device? | Notes |
|---|---|---|
| Category + sanitized message to local Ollama | Stays on localhost | Only in `local_llm` mode, for `other_error` or confidence < 0.7 |
| Sanitized error message | Opt-in cloud modes only (future) | Only after redaction |
| Error category (e.g. `key_error`) | Opt-in cloud modes only (future) | |
| Abstract stack summary | Opt-in cloud modes only (future) | Not implemented yet |
| Fingerprint / hash | Opt-in cloud modes only (future) | |
| Raw, unsanitized error text | **Never** | |
| Full file contents or source code | **Never** | |
| Raw screenshots or OCR output | **Never** | |
| Absolute file paths with real usernames | **Never** | |
| Real email addresses, API keys, tokens | **Never** | |
| Environment variable values | **Never** | |
| URL credentials | **Never** | |

## Keyboard Input

The widget only handles keys (Escape) while it has focus. No global hotkeys or system-wide keyboard hooks are used, so the application never sees keystrokes meant for other programs.

## Where Sanitization Happens in the Pipeline

Sanitization runs in `dmrun.py`, immediately after parsing the error and before fingerprinting. This ordering is deliberate: fingerprinting the sanitized text (rather than the raw text) means the fingerprint reflects the meaningful content of the error, not incidental sensitive details like a username in a file path. It also guarantees no sensitive data reaches the fingerprint, the debounce state file, the ML classifier, or any downstream service, local or (in the future) cloud.

## Risk Scoring (Fail-Closed Safety Net)

After sanitization, `assess_risk()` performs a second, stricter check on the already-sanitized text. It flags any remaining alphanumeric run of 16+ characters that contains a digit, which is how most leftover secrets look. Plain letter-only runs are ignored, so ordinary exception names such as `NewConnectionError` do not block legitimate errors. The 16-character threshold is deliberately lower than `sanitize_tokens()`'s 20-character cutoff.

If `assess_risk()` returns `"review"`, the error is **not sent anywhere**. It is reported locally in the terminal with a notice, and the request to the local service is skipped entirely. This is the fail-closed principle in practice: when in doubt, don't send it.

## Data Stored Locally

- `client/.debounce_state.json`: fingerprints (hashes of sanitized errors) and timestamps. No raw text.
- `local_service/settings.json`: privacy mode and confidence threshold.
- The latest result is held in memory by the service and is lost on restart.
- `ml_engine/data/labeled/dataset.csv`: sanitized, generated training examples only. No user errors are collected.

## Known Limitations

- Unix paths containing spaces (e.g. "/home/user/My Documents/file.py") are only partially redacted, because the pattern stops at the first space. This is low-risk in practice, and handling spaces risks new false positives elsewhere.
- Windows paths using forward slashes (C:/Users/...) leave the bare drive letter (e.g. "C:") visible. A drive letter alone isn't meaningfully sensitive.
- `sanitize_tokens()` redacts any identifier of 20+ characters, so some harmless long names are redacted too. Over-redaction is accepted as safer than missing a secret.
- Regex-based redaction cannot guarantee that every secret is caught. `assess_risk()` is a second net, not a proof.
- LLM output is generated text and can be wrong. It is labelled as such in the widget.
- `assess_risk()` only flags 16+ character runs that contain a digit, to avoid blocking ordinary exception names. A secret of 16-19 letters with no digits would pass both `sanitize_tokens()` (20+ characters) and `assess_risk()`.