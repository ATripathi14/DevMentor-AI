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

DevMentor AI uses a **"push" model** instead. It doesn't wait for you to ask. It detects the error and shows an explanation automatically, as soon as it happens.

The goal is to automate the low-value part of debugging (figuring out what an error means) so you can spend your time on the part that matters: understanding and applying the fix.

## Why This Is Different

| Dimension | Tools like GitHub Copilot | DevMentor AI |
|---|---|---|
| **Trigger** | Reactive: you ask it | Proactive: it notices and tells you |
| **Scope** | Trapped inside one IDE | Works from any terminal when you launch code through the `dmrun` wrapper |
| **Data handling** | Sends context to the cloud by default | Local-first; nothing leaves the device unless you opt in |
| **Cost/latency model** | Every query round-trips to an LLM | Local ML classifier and rules handle most errors instantly; a local LLM is optional |

## How It Works

1. **Capture**: You run your program through `dmrun` (e.g. `python client/dmrun.py python app.py`). It captures stderr and extracts the error type and message.
2. **Sanitize**: A local privacy engine redacts file paths, emails, tokens, environment values, URL credentials, memory addresses and IPv4 addresses (except localhost). A second check (`assess_risk`) blocks anything still suspicious from being sent anywhere (fail closed).
3. **Deduplicate**: The sanitized error is fingerprinted, and repeats within 60 seconds are suppressed.
4. **Classify**: A local FastAPI service runs a calibrated ML classifier. If its confidence is at or above the threshold (0.6 in `settings.json`), the ML category is used. Otherwise it falls back to a deterministic rules mapping.
5. **Explain**: A floating, always-on-top widget shows a plain-English explanation, labelled with its confidence, or "pattern-matched" if the rules path was used. In `local_llm` mode, hard or low-confidence errors are upgraded with a local AI explanation, labelled as AI-generated.

**Scope:** DevMentor captures errors from scripts launched through `dmrun`. It does not watch an arbitrary terminal or the interactive Python prompt.

## MVP Demo

DevMentor detects Python errors in real time and provides plain-English explanations directly in a floating desktop widget.

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

- **Desktop client**: `dmrun` wrapper, floating widget
- **Local intelligence**: sanitization, parsing, ML inference, rule engine, optional local LLM
- **Local service**: FastAPI on localhost connecting the client and the intelligence layer
- **Hosted backend (later phase)**: auth, sync, quotas, audit, LLM routing; entirely optional

## Privacy Model

Privacy isn't a feature bolted on afterward. It is the core design constraint. Full details are in [docs/privacy_model.md](docs/privacy_model.md).

- **Local-first by default.** Local Only mode makes zero cloud requests.
- **Fail closed.** If the sanitizer isn't confident content is safe, it blocks transmission. It never guesses in favor of sending.
- **Least data necessary.** Only the error type, the sanitized message and the category are ever used, never whole files, raw screenshots, or raw OCR output.
- **No global keyboard hooks.** The widget only handles Escape while it has focus.

| Mode | Default | Behavior |
|---|---|---|
| Local Only | Yes | No LLM calls: rules + local ML only |
| Local LLM | No | Sanitized message sent to a local Ollama process on localhost, only for hard or low-confidence errors |
| Sanitized Cloud | No | Planned: sends only approved, re-sanitized metadata for a richer explanation |
| Advanced Cloud | No | Planned: user-approved redacted snippets, configurable provider |

Local Only (default) and optional Local LLM are implemented; the cloud modes are planned.

## ML Engine

A text-classification pipeline trained on 132 labelled, sanitized error messages across 12 categories. The training data was generated by running small failing code snippets. The model is evaluated separately on real-world errors (see below).

- **Features**: TF-IDF (1-2 grams) over `"{error_type} {message}"`. Including the exception type fixed `key_error` and `other_error`, which scored 0.00 on message text alone.
- **Model**: Linear SVM wrapped in `CalibratedClassifierCV` so it produces usable probabilities. Chosen over Logistic Regression and Multinomial Naive Bayes after comparison.

| Model | Macro F1 (3-fold CV, generated data) |
|---|---|
| Logistic Regression | 0.801 |
| Linear SVM | 0.957 |
| Linear SVM (calibrated, **used**) | 0.931 |
| Multinomial Naive Bayes | 0.661 |

**Real-world evaluation.** 237 errors collected from public GitHub issues, sanitized and labelled by hand, with any rows that overlap the training data removed:

| Path | Macro F1 |
|---|---|
| ML model alone | 0.773 |
| Full pipeline (ML + rules fallback) | 0.875 |

The real-world numbers are the ones to trust. The rules fallback adds about 10 macro F1 points over the model alone, and roughly 39% of real errors are routed to it.

- **Known weaknesses**: the model over-predicts `other_error` on unfamiliar wording, and `network_error` and `none_type_error` are the weakest categories. `none_type_error` shares message templates with `attribute_error` and `type_error`.
- **Honest caveats**: the model is trained only on generated messages. The real-world set is used for evaluation only, and it has now informed design decisions, so it is a dev set rather than an unbiased test. Some categories have fewer than 15 evaluation rows, so their scores move a lot per prediction.
- **Reproducible**: `python ml_engine/train.py` rebuilds the saved model from `dataset.csv`. The notebook `ml_engine/notebooks/training_and_evaluation.ipynb` is the authoritative record; the `_scratch` notebooks are archived history. See `ml_engine/models/model_card.md` for details.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Local API | FastAPI + Uvicorn |
| Desktop UI | PySide6 |
| ML | scikit-learn (TF-IDF, LinearSVC + CalibratedClassifierCV), pandas, joblib |
| Sanitization | `re` / regex-based pattern matching |
| Optional local LLM | Ollama (`llama3.2:3b`) |
| Testing | pytest (38 tests) |

*Planned, not used yet: SQLite, OCR (Tesseract), PostgreSQL, Redis, Docker, PyInstaller.*

## Project Status

**v1.1: Python-only, local-first.** The core pipeline, privacy layer, ML classifier, widget and optional local LLM mode are complete.

- [x] Foundation
- [x] Local MVP (`dmrun`, FastAPI service, floating widget)
- [x] Privacy layer (sanitizer, risk scorer, settings)
- [x] ML engine (dataset, model comparison, calibrated classifier wired into `/analyze`)
- [x] Widget polish: threaded polling, collapse, light/dark theme, Escape to hide, tray icon
- [x] Local LLM mode (Ollama)
- [x] Real-world evaluation set and honest baseline
- [x] 38 passing tests (pytest)
- [ ] Final demo video
- [ ] v2: multi-language support, capture beyond `dmrun`, real-data training

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

**Run the tests:**

```bash
pytest -v
```

**Real-world evaluation (optional).** The collection scripts need a GitHub token in a `.env` file at the project root (`GITHUB_TOKEN=...`) and the `python-dotenv` package. Raw collected data stays local and is gitignored.

```bash
python ml_engine/collect_github.py     # collect public issue tracebacks (local only)
python ml_engine/collect_eval.py       # sanitize and prepare files for labeling
python ml_engine/check_eval.py         # validate labels, check overlap with training
python ml_engine/evaluate_real.py      # score the saved model
```

## Roadmap

**v1.1 (current):** Python-only, 132-example generated training set, calibrated Linear SVM classifier, rules fallback, optional local LLM mode via Ollama.

**Direction:** a language-agnostic, tiered system (error codes, templates, an ML cause classifier, optional local LLM) with capture beyond `dmrun`.

**v2 (planned):**

- **Real-world training data**: a larger set of sanitized real-world tracebacks, with a separate frozen test set for honest evaluation
- **Multi-language support**: JavaScript and Java first, then others (C++, Go, Rust), with a parser, error-code table and evaluation set per language
- **Better explanations**: slot-filled explanations that use names from the error message, and a cause taxonomy discovered from real data instead of the fixed 12 categories
- **Broader capture**: a `sys.excepthook` interpreter mode, shell integration and a VS Code terminal extension

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
    data/
      raw/           # source scripts for the generated dataset
      labeled/       # dataset.csv (training data)
      eval/          # real-world evaluation data (eval_labeled.csv)
    models/          # saved model, charts, model card
    notebooks/       # training_and_evaluation.ipynb (+ archived scratch)
    train.py
    collect_github.py, collect_eval.py, prelabel.py,
    check_eval.py, evaluate_real.py
  docs/              # architecture, privacy model, notes, demo
  test/              # fixtures
  pyproject.toml
  LICENSE
  README.md
```

---

*A work in progress. See [Project Status](#project-status) for what is actually working right now.*