# DevMentor AI — Privacy Model

This document describes exactly what data DevMentor AI collects, processes, and (if ever) transmits — and what it never touches at all.

## Current State (Local-Only Mode)

As of Week 4, DevMentor AI operates entirely locally. No error data, sanitized or otherwise, is ever sent outside your own machine. The sanitizer described below exists to prepare the project for optional, future cloud-assisted modes (see Roadmap) — but right now, sanitized text only ever travels between two processes on localhost: dmrun.py and the local FastAPI service.

## What Gets Sanitized, and Why

Before an error message is fingerprinted, stored, or sent anywhere — even to the local service — it passes through sanitize(), which strips:

| Sensitive data type | Redacted as | Example |
|---|---|---|
| File paths (Windows & Unix) | [REDACTED_PATH] | C:\Users\name\file.py → [REDACTED_PATH] |
| Email addresses | [REDACTED_EMAIL] | john@example.com → [REDACTED_EMAIL] |
| Long tokens / API keys (20+ chars) | [REDACTED_TOKEN] | sk_live_51H8x... → [REDACTED_TOKEN] |
| Environment variable values | [REDACTED_VALUE] | SECRET_KEY=abc123 → SECRET_KEY=[REDACTED_VALUE] |
| Credentials embedded in URLs | [REDACTED_CREDENTIALS] | https://user:pass@host → https://[REDACTED_CREDENTIALS]@host |

## Data Handling Summary

| May leave the device (opt-in cloud modes, future) | NEVER sent, in any mode |
|---|---|
| Sanitized error message | Raw, unsanitized error text |
| Error category (e.g. "key_error") | Full file contents or source code |
| Abstract stack summary (future) | Raw screenshots or OCR output |
| Fingerprint/hash | Absolute file paths with real usernames |
| | Real email addresses, API keys, tokens |
| | Environment variable values |
| | URL credentials |

## Known Limitations

- Unix paths containing spaces (e.g. "/home/user/My Documents/file.py") are only partially redacted — the pattern stops at the first space. Considered low-risk in practice (error tracebacks rarely contain spaced folder names) and not worth the added regex complexity, which risks introducing new false positives elsewhere.

- Windows paths using forward slashes (C:/Users/...) leave the bare drive letter (e.g. "C:") visible — a minor leak, since a drive letter alone isn't meaningfully sensitive.

- none_type_error classification is currently unreachable (see architecture.md) — unrelated to sanitization, but noted here since it affects the same message-processing pipeline.

## Where Sanitization Happens in the Pipeline

Sanitization runs in dmrun.py, immediately after parsing the error and before fingerprinting. This ordering is deliberate: fingerprinting the sanitized text (rather than the raw text) means the fingerprint reflects the meaningful content of the error, not incidental sensitive details like a username in a file path — and guarantees no sensitive data ever reaches the fingerprint, the debounce state file, or any downstream service, local or (in the future) cloud.