# DevMentor AI

**A Proactive, Real-Time AI Debugging & Code Comprehension Assistant**

> DevMentor AI is a privacy-first desktop tool that detects errors in your code and shows a plain-English explanation in a floating widget — no copying, no pasting, no switching windows.

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Why This Is Different](#why-this-is-different)
- [How It Works](#how-it-works)
- [MVP Demo](#mvp-demo)
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
| **Cost/latency model** | Every query round-trips to an LLM | Local rule engine + ML classifier handle most errors instantly; a local LLM is optional |

The key feature is zero-click detection: the widget can respond before you've reached for the mouse.

## How It Works

1. **Capture**: You run your program through `dmrun` (e.g. `python client/dmrun.py python app.py`). It captures stderr and extracts the error type and message.
2. **Sanitize**: A local privacy engine redacts file paths, emails, tokens, env values, URL credentials and memory addresses. A second check (`assess_risk`) blocks anything still suspicious from being sent anywhere (fail closed).
3. **Deduplicate**: The sanitized error is fingerprinted, and repeats within 60 seconds are suppressed.
4. **Classify**: A local FastAPI service runs a calibrated ML classifier. If its confidence is at or above the threshold (0.6 in `settings.json`), the ML category is used. Otherwise it falls back to a deterministic rules mapping.
5. **Explain**: A floating, always-on-top widget shows a plain-English explanation, labelled with its confidence or "pattern-matched" if the rules path was used. In `local_llm` mode, hard or low-confidence errors are upgraded with a local AI explanation, labelled as AI-generated.

**Scope:** DevMentor captures errors from scripts launched through `dmrun`. It does not watch an arbitrary terminal or the interactive Python prompt.

## MVP Demo

DevMentor detects Python errors in real time and provides
plain-English explanations directly in a floating desktop widget.

<video src="https://github.com/user-attachments/assets/9f242c6e-349d-4c0e-8a48-77a90c715378" controls="controls" muted="muted" width="100%"></video>

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

- **Desktop client** — `dmrun` wrapper, floating widget
- **Local intelligence** — sanitization, parsing, ML inference, rule engine, optional local LLM
- **Local service** — FastAPI on localhost connecting the client and the intelligence layer
- **Hosted backend (later phase)** — auth, sync, quotas, audit, LLM routing — entirely optional

## Privacy Model

Privacy isn't a feature bolted on afterward — it's the core design constraint. Full details are in [docs/privacy_model.md](docs/privacy_model.md).

- **Local-first by default.** Local Only mode makes zero cloud requests.
- **Fail closed.** If the sanitizer isn't confident content is safe, it blocks transmission and asks you to review it — it never guesses in favor of sending.
- **Least data necessary.** Only error type, sanitized message, and category are ever used — never whole files, raw screenshots, or raw OCR output.
- **No global keyboard hooks.** The widget only handles Escape while it has focus.

| Mode | Default | Behavior |
|---|---|---|
| Local Only | Yes | No LLM calls — rules + local ML + local history only |
| Local LLM | No | Sanitized message sent to a local Ollama process on localhost, only for hard or low-confidence errors |
| Sanitized Cloud | No | Planned: sends only approved, re-sanitized metadata for a richer explanation |
| Advanced Cloud | No | Planned: user-approved redacted snippets, configurable provider |

Local Only (default) and optional Local LLM are implemented; the cloud modes are planned.

## ML Engine

A text-classification pipeline trained on 132 labelled, sanitized error messages across 12 categories, generated by running small failing code snippets (not real-world tracebacks).

- **Features**: TF-IDF (1-2 grams) over `"{error_type} {message}"`. Including the exception type fixed `key_error` and `other_error`, which scored 0.00 on message text alone.
- **Model**: Linear SVM wrapped in `CalibratedClassifierCV` so it produces usable probabilities. Chosen over Logistic Regression and Multinomial Naive Bayes after comparison.
- **Evaluation**: 3-fold stratified cross-validation, since a held-out 10% test set covered only 7 of 12 categories.

| Model | Macro F1 (3-fold CV) |
|---|---|
| Logistic Regression | 0.801 |
| Linear SVM | 0.957 |
| Linear SVM (calibrated, **used**) | 0.931 |
| Multinomial Naive Bayes | 0.661 |

- **Known weakness**: `none_type_error` is confused with `attribute_error` and `type_error`, because NoneType errors reuse the same message templates. Low-confidence cases route to the rules fallback.
- **Honest caveat**: these scores are on generated messages. Real-world accuracy is likely lower; a real dataset is planned for v2.
- **Reproducible**: `python ml_engine/train.py` rebuilds the saved model from `dataset.csv`. The notebook `ml_engine/notebooks/training_and_evaluation.ipynb` is the authoritative record; the `_scratch` notebooks are archived history.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Local API | FastAPI + Uvicorn |
| Desktop UI | PySide6 |
| ML | scikit-learn (TF-IDF, LinearSVC + CalibratedClassifierCV), pandas, joblib |
| Sanitization | `re` / regex-based pattern matching |
| Optional local LLM | Ollama (`llama3.2:3b`) |
| Testing | pytest (31 tests) |

*Planned, not used yet: SQLite, OCR (Tesseract), PostgreSQL, Redis, Docker, PyInstaller.*

## Project Status

**In active development.** Phases 0 to 3 and the local LLM mode are complete; the final wrap-up is in progress.

- [x] Phase 0: Foundation
- [x] Phase 1: Local MVP (`dmrun`, FastAPI service, floating widget)
- [x] Phase 2: Privacy layer (sanitizer, risk scorer, settings)
- [x] Phase 3: ML engine (dataset, model comparison, calibrated classifier wired into `/analyze`)
- [x] Widget polish: threaded polling, collapse, light/dark theme, Escape to hide, tray icon
- [x] Local LLM mode (Ollama)
- [x] 31 passing tests (pytest)
- [ ] Final stress test, model card, demo video, v1.0
- [ ] Optional: feedback loop, knowledge graph, OCR, VS Code extension

## Getting Started

```bash
git clone https://github.com/ATripathi14/DevMentor-AI.git
cd DevMentor-AI
conda create -n devmentor python=3.11
conda activate devmentor
pip install -e ".[dev]"
```

Train the model (writes `classifier.joblib` and `vectorizer.joblib`):

```bash
python ml_engine/train.py
```

Run it in three terminals:

```bash
# Terminal 1: the local service (leave running)
uvicorn local_service.main:app --reload --port 8765

# Terminal 2: the floating widget
python client/widget.py

# Terminal 3: run a broken script through dmrun
python client/dmrun.py python ml_engine/data/raw/Key_Error.py
```

This captures the error, classifies it into one of 12 categories, and prints a plain-English explanation and suggested fix in the terminal. The widget updates within about 2 seconds. If the local service isn't running, `dmrun` still shows the raw error along with a message telling you how to start it. Running the same broken script again within 60 seconds is suppressed rather than shown twice (debounce).

**Optional local LLM mode:** install Ollama, run `ollama pull llama3.2:3b`, then set `"privacy_mode": "local_llm"` in `local_service/settings.json`. It is used only for hard or low-confidence errors and takes roughly 10 seconds, after the instant explanation has already appeared.

Run the tests:

```bash
pytest -v
```

## Roadmap

**v1.0:** Python-only, 132-example generated dataset, calibrated Linear SVM classifier, optional local LLM mode via Ollama.

**v2 (planned):** A real-world dataset and multi-language support.

- **Real-world traceback dataset**: thousands of sanitized tracebacks collected from public sources, with a hand-labeled holdout set for honest evaluation
- **Multi-language error support**: JavaScript and Java first, then others (C++, Go), with language detection and per-language classifiers
- **Interpreter hook**: a `sys.excepthook` mode so errors in interactive sessions are captured too

**Later enhancements:**

- **Feedback loop**: let users rate explanations and use that data for periodic retraining
- **Explainability panel**: show which tokens drove a given classification

## Project Structure

```
DevMentor-AI/
  client/            # dmrun.py, runner.py, widget.py
  local_service/     # FastAPI service, classifier_service, explainer,
                     # llm_adapter, settings, API tests
  sanitizer/         # redaction functions, risk scorer, tests
  ml_engine/
    data/            # raw/ (source scripts), labeled/ (dataset.csv)
    models/          # saved model, charts, model card
    notebooks/       # training_and_evaluation.ipynb (+ archived scratch)
    train.py
  docs/              # architecture, privacy model, notes, demo
  test/              # fixtures
  pyproject.toml
  LICENSE
  README.md
```

---

*A work in progress — see [Project Status](#project-status) for what's actually working right now.*