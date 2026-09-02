# DevMentor AI

**A Proactive, Real-Time AI Debugging & Code Comprehension Assistant**

> DevMentor AI is a privacy-first desktop tool that detects errors in your code and shows a plain-English explanation in a floating widget — no copying, no pasting, no switching windows.

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Why This Is Different](#why-this-is-different)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Privacy Model](#privacy-model)
- [ML Engine](#ml-engine)
- [Tech Stack](#tech-stack)
- [Project Status](#project-status)
- [Getting Started](#getting-started)
- [Roadmap](#roadmap)
- [Project Structure](#project-structure)

---

## The Problem

Every developer, from beginner to experienced, runs into the same interruption when debugging:

1. Run code
2. See a cryptic error (`TypeError: 'NoneType' object is not iterable`)
3. Stop working on the actual logic
4. Copy the error
5. Paste it into Google, Stack Overflow, or a chatbot
6. Look through the results for an answer
7. Return to the code and pick up where you left off

This is a **"pull" model** of debugging: you have to stop and go find help. It interrupts your focus every time, even for routine errors that don't need a full context switch.

## The Solution

DevMentor AI uses a **"push" model** instead. It doesn't wait for you to ask — it detects the error and shows an explanation automatically, as soon as it happens.

The goal is to automate the low-value part of debugging (figuring out what an error means) so you can spend your time on the part that matters: understanding and applying the fix.

## Why This Is Different

| Dimension | Tools like GitHub Copilot | DevMentor AI |
|---|---|---|
| **Trigger** | Reactive — you ask it | Proactive — it notices and tells you |
| **Scope** | Trapped inside one IDE | Works with any terminal via a command wrapper |
| **Data handling** | Sends context to the cloud by default | Local-first; nothing leaves the device unless you opt in |
| **Cost/latency model** | Every query round-trips to an LLM | Local rule engine + ML classifier handle most errors instantly; cloud is a last resort |

The key feature is zero-click detection: the widget can respond before you've reached for the mouse.

## How It Works

1. **Capture** — You run your program through `dmrun` (e.g. `dmrun python app.py`). It transparently wraps the process and captures stdout/stderr/exit code the moment something fails. (An optional, off-by-default OCR mode can watch a user-selected terminal region for cases where a wrapper isn't practical — see [Privacy Model](#privacy-model).)
2. **Sanitize** — A local privacy engine strips paths, tokens, emails, credentials, and env values before anything is stored or analyzed.
3. **Understand** — A local ML classifier identifies the error category (and filters out normal/non-error output) in milliseconds. A similarity engine checks whether this error has been explained before.
4. **Explain** — A floating, always-on-top widget shows a plain-English explanation and suggested next steps — instantly, from local inference. If you've opted into cloud assistance, only sanitized metadata is sent upstream for a richer explanation.
5. **You stay in flow** — Copy a suggestion, mark it helpful, or dismiss it, and keep coding.

## Architecture

*This shows the target end-state architecture. For the current, as-built pipeline, see [docs/architecture.md](docs/architecture.md).*

```
Desktop Client
  dmrun wrapper / optional OCR
          ↓
  Local privacy engine + parser + ML engine
          ↓
  Local API/service + floating widget
          ↓ (only sanitized, approved payload)
Hosted API → queue/cache → LLM provider → validated response
          ↓
     WebSocket/poll update to widget
```

- **Desktop client** — `dmrun` wrapper, optional OCR control, floating widget, settings/consent UI
- **Local intelligence** — sanitization, parsing, ML inference, rule engine, local cache
- **Local service** — FastAPI on localhost connecting the client and the intelligence layer
- **Hosted backend (later phase)** — auth, sync, quotas, audit, LLM routing — entirely optional

## Privacy Model

Privacy isn't a feature bolted on afterward — it's the core design constraint.

- **Local-first by default.** Local-Only mode makes zero cloud requests.
- **Fail closed.** If the sanitizer isn't confident content is safe, it blocks transmission and asks you to review it — it never guesses in favor of sending.
- **Least data necessary.** Only error type, language, sanitized message, and an abstract stack summary are eligible to leave the device — never whole files, raw screenshots, or raw OCR output.
- **Re-sanitized server-side.** The client is never trusted alone; anything that reaches a hosted backend is checked again.

| Mode | Default | Behavior |
|---|---|---|
| Local Only | Yes | No hosted API/LLM calls — rules + local ML + local history only |
| Sanitized Cloud | No | Sends only approved, re-sanitized metadata for a richer explanation |
| Advanced Cloud | No | User-approved redacted snippets, configurable provider — still never raw screenshots |

## ML Engine

This is a genuine machine learning subsystem, not an LLM API wrapper:

- **Error category classifier** — TF-IDF features with Logistic Regression / Linear SVM comparison across 12 Python error classes (`syntax_error`, `type_error`, `key_error`, `module_not_found`, etc.), selected by **macro F1** to avoid common classes dominating the score.
- **Log state classifier** — separates `error` / `warning` / `normal_log` / `unknown` to cut down false popups.
- **Similarity retrieval** — cosine similarity over TF-IDF vectors to reuse cached explanations for errors seen before, cutting latency and cloud calls.
- **Confidence thresholding** — low-confidence predictions route to a safer fallback instead of guessing.

Evaluation artifacts (confusion matrix, per-class F1, model card) live in `ml_engine/` once training begins.

## Tech Stack

*Target stack for the full project — not everything below is wired up yet (see [Project Status](#project-status)).*

| Layer | Technology |
|---|---|
| Language | Python |
| Local/hosted API | FastAPI + Uvicorn |
| Desktop UI | PySide6 |
| ML | scikit-learn (TF-IDF, Logistic Regression, LinearSVC), pandas, joblib |
| Sanitization | `re` / regex-based pattern matching |
| Local storage | SQLite |
| Optional OCR | Tesseract + pytesseract, mss |
| Hosted backend (later) | PostgreSQL, Redis, Docker Compose |
| Packaging | PyInstaller |
| Testing | pytest |

## Project Status

**In active development.** Currently in Phase 1 (Local MVP) — Week 2, 
Day 5 complete.

- [x] Phase 0 — Foundation (environment, Git, 12 broken scripts, error anatomy)
- [ ] Phase 1 — Local MVP (in progress)
  - [x] `dmrun` wrapper: captures and parses errors via subprocess
  - [x] Error fingerprinting + debounce (persisted across runs)
  - [x] Local FastAPI service with `/analyze` and `/latest` endpoints
  - [x] Rule-based explanations for all 12 error categories
  - [x] 4 passing API tests (pytest)
  - [ ] Floating widget (PySide6)
- [ ] Phase 2 — Privacy Layer
- [ ] Phase 3 — ML Engine
- [ ] Phase 4 — UX polish + optional OCR
- [ ] Phase 5 — Cloud assist & productization *(stretch)*

## Getting Started

```bash
git clone https://github.com/ATripathi14/DevMentor-AI.git
cd DevMentor-AI
conda create -n devmentor python=3.11
conda activate devmentor
pip install -e .
```

**Try it out:**

Start the local service (leave this running in its own terminal):

```bash
uvicorn local_service.main:app --reload --port 8765
```

In a separate terminal, run a broken script through `dmrun`:

```bash
python client/dmrun.py python ml_engine/data/raw/Key_Error.py
```

This captures the error, classifies it into one of 12 categories, and 
prints a plain-English explanation and suggested fix. If the local 
service isn't running, `dmrun` still shows the raw error along with a 
message telling you how to start it. Running the same broken script 
again within 60 seconds is automatically suppressed rather than shown 
twice — this is the debounce logic in action.

> The floating widget is next up in Phase 1.

## Roadmap

Planned work after the MVP:

- **Multi-language error support** — extend the classifier beyond Python to JavaScript and Java
- **Feedback loop** — let users rate explanations and use that data for periodic retraining
- **Local LLM mode (Ollama)** — richer explanations with no cloud dependency
- **Explainability panel** — show which tokens drove a given classification

Detailed architecture and privacy-model docs will be added to `docs/` as each phase lands.

## Project Structure

```
DevMentor-AI/
  client/              # dmrun, widget, OCR, consent UI
  local_service/       # FastAPI localhost service, rules, sanitizer
  ml_engine/
    data/ notebooks/ src/ models/ tests/
  backend/             # hosted API, auth, queue workers (later)
  docs/                # architecture, privacy model, model card
  tests/               # end-to-end tests
  .env.example
  README.md
```

---

*A work in progress, built one phase at a time — see [Project Status](#project-status) for what's actually working right now.*