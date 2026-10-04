Day 1 — Environment + Git setup

1. Set up the devmentor conda environment, confirmed python and conda work cleanly.
2. Created the project folder structure and initialized the Git repo.
3. Wrote the first README and pushed the initial commit to github.com/ATripathi14/DevMentor-AI.


Day 2 — 12 broken scripts (labeled dataset)

1. Wrote one deliberately broken script per error category: syntax_error, type_error, none_type_error, key_error, index_error, attribute_error, module_not_found, file_not_found, permission_error, value_error, network_error, other_error.
2. Ran each one and read the traceback to confirm it actually raises the intended exception (not a different one by accident).
3. Committed and pushed to main — they're the ground for the TF-IDF training data later in Phase 3.


Day 3 — Building the error capturer (client/runner.py)

1. Reading subprocess.run() docs — focusing only on capture_output, text, returncode.
2. Writing get_output_error(script_path): runs a script, returns stderr as a string on failure, None on success.
3. Windows/conda note: shelling out to a bare "python" string relies on whatever python resolves to on PATH, which may not match the active conda environment. Using sys.executable which instead guarantees the subprocess runs with the exact same interpreter — and therefore the same environment — that the script is already running in.

Key Points learned :
   
    -used sys.executable instead of python becuase "python" relies on PATH search order to guess the right interpreter — risky when multiple Pythons exist on a machine. "sys.executable" always points to the exact interpreter currently running your code, so it's guaranteed correct regardless of environment or machine.

    -subprocess.run() returns a CompletedProcess object, which has a returncode attribute that you can check to see if the process completed successfully or not.

    -"capture_output = True" tells subprocess to capture the stdout and stderr streams and store them in the CompletedProcess object's stdout and stderr attributes.

    -"text = True" tells subprocess to decode the stdout and stderr streams into strings, which are then stored in the CompletedProcess object's stdout and stderr attributes.

4. Confirmed outputs: None returned correctly when a script runs successfully with no errors, and the correct   stderr string returned when a script fails — tested against 3 broken scripts and 1 working script.
5. Wrote parse_error(stderr_text) extracting error type and message from the final traceback line. Uses split(":", 1) to avoid breaking on messages that contain colons themselves.
6. Built client/dmrun.py — a command-line entry point that ties everything together: run `python dmrun.py python your_script.py`, and it captures the error, parses it, and prints the result in one step.
7. Tested all 12 scripts through dmrun.py — found and fixed bugs that may have caused issues later on.



Day 4 — Fingerprinting and Debounce

1. fingerprint(error_type, message): returns a short (12-char) hash uniquely and stably identifying an error.
Same inputs -> same hash, every time. Used as a compact ID instead of comparing raw error text.

2. should_notify(fp, window_seconds=60): returns False if the same fingerprint was seen within the last 
window_seconds (suppress repeat notification); otherwise records the current time and returns True.

3. Debounce state (fingerprint->last_seen_timestamp) is persisted to client/.debounce_state.json instead of an  in-memory dict. Reason: dmrun.py exits after every run , so an in-memory dict would reset to empty each   invocation, making debounce never actually suppress anything across separate runs. Persisting to disk lets state survive between runs.

4. .debounce_state.json is auto-created on first write, never created manually, and is gitignored 
(runtime-generated, not source).

5. Hit an import resolution issue (ModuleNotFoundError) when running scripts from nested folders. 
Fixed by adding __init__.py files and switching to an editable install (pip install -e .) via pyproject.toml, which makes the project importable from any location without sys.path hacks.

Day 5 — Refactor, documentation, and v0.1 tag

1. Reviewed runner.py and dmrun.py line by line: fixed inconsistent comment formatting, and added proper    docstrings to parse_error() and fingerprint() (they previously used # comments instead of """docstrings""").

2. Renamed the unclear variable fp to fingerprint_id in dmrun.py for readability — a plain comment wasn't enough context on its own when reading the file top to bottom.

3. Re-ran all 12 broken scripts through dmrun.py to confirm today's changes hadn't broken anything — all 12 still produced correct output.

4. Updated README's Project Status section to accurately reflect progress .

5. Wrote docs/architecture.md documenting the current, as-built pipeline (separate from the target architecture shown in README).

6. Tagged v0.1-foundation on GitHub, marking Foundation as complete.

   
SUMMARY OF THE WEEK -

1. I learned how a project setup is created and managed, how git works at basic level and how you think through your plan multiple times to find the gap of what is required from the project rather than what you really want it to become .

2. I now understand the project's architecture better, including what each function is responsible for and why clear naming conventions matter.

3. Since I have hit real friction with imports I also somewhat got the idea of importing modules across a project  but i still need to learn about it more.


Known issues — to address during dataset enhancement

- normalize_error_type() currently can't distinguish NoneType errors. They surface as TypeError 
  or AttributeError with "NoneType" in the message text, not as their own exception class — 
  so none_type_error is currently unreachable as a category output. Needs message-content checking 
  (not just exception-name lookup) to fix properly.

- RecursionError is not yet in ERROR_TYPE_TO_CATEGORY — currently falls through to the default 
  "other_error" via .get()'s fallback, which is correct behavior but not an explicit, intentional mapping yet.

- Broken script filenames in ml_engine/data/raw/ have inconsistent casing (e.g. Key_Error.py vs 
  network_Error.  py vs permission_Error.py). Worth standardizing (matching category label strings) when 
  rewriting/expanding scripts for the ML dataset.

- Zero_division_Error.py intentionally maps to the "other_error" category, not a dedicated
  13th label — keeping the official label set at 12 categories.

Week 2 — Local API (FastAPI)

1. Built a FastAPI server (main.py) running on port 8765, starting with a basic health-check route.

2. Wrote explainer.py — a dictionary mapping all 12 error categories to plain-English explanations, plus a mapping from raw Python exception names to those 12 labels.

3. Built the POST /analyze endpoint. It takes error_type, message, and fingerprint, figures out the category, looks up the explanation, and sends it back. Pydantic automatically rejects bad requests before my code even runs.

4. Connected dmrun.py to this endpoint using requests.post(), instead of just printing the error locally.

5. Added GET /latest, which remembers the most recent result in a plain dictionary in memory. This is fine here since the server keeps running, unlike dmrun.py which exits every time.

6. Wrote 4 pytest tests using FastAPI's TestClient to check known errors, unknown errors, /latest updating, and bad requests getting rejected.

Bugs I found and fixed:
- My mapping only matched plain exception names like "ConnectionError", but errors from the requests library show up as "requests.exceptions.ConnectionError" — a longer, fully-qualified name. Had to add that as its own mapping.
- dmrun.py would crash with a huge network traceback if the server wasn't running. Fixed it to catch that specific error and show a short, clear message instead.
- My first draft of the 12 explanations sounded like textbook definitions, not something a person would actually say. Rewrote all of them to lead with a real example and a clear next step.

Known gap I'm leaving for later: none_type_error can never actually get chosen right now, because NoneType errors show up as TypeError or AttributeError, not their own error type. I'll fix this properly in Week 5 when I build the real dataset.

Something I learned: pytest tests my code's logic without needing a real server running. Manually running dmrun against a live server tests something different — whether the whole system actually works together. Both matter, and one doesn't replace the other.


Week 3 — Floating Widget (PySide6)

1. Built the widget: always-on-top, fixed size, positioned in the top-right corner.

2. Made it poll /latest every 2 seconds and only update when the error is genuinely new — had to add fingerprint to the API responses for this to work.

3. Added Dismiss (hides, doesn't close) and Copy buttons.

4. Added a system tray icon with a menu (Show Widget, Exit) and made single-click toggle the widget too.

5. Recorded a short demo video of the whole thing working live.

Bugs I found and fixed:
- Accidentally deleted the line that attaches the layout to the window while adding the Copy button. The window just showed up blank — no error, no crash. Found it by comparing screenshots from before and after.
- Handling single-click and double-click the same way meant double-clicking toggled the widget twice, cancelling itself out. Fixed by only reacting to single-click.
- The Copy button didn't give any feedback, so I couldn't tell if it worked. Added a quick "Copied!" message on the button for a second.

A design choice I thought through and kept: if I trigger error A, then error B, then error A again quickly, the second error A still gets suppressed — even though something else happened in between. I initially expected this to feel wrong, but it's actually correct: debounce is about not repeating the same error, not about "what was shown last." If it worked the other way, you could dodge debounce completely just by alternating between two errors.

Phase 1 is done as of v0.3-mvp-complete — the whole thing works end to end now. Break a script, and the widget shows the explanation automatically, no extra steps.

Week 4 — Sanitizer

1. Learned regex basics: \w, \d, \s, ., *, +, character sets, and re.sub() for find-and-replace.

2. Wrote sanitize_paths() — redacts Windows paths (C:\Users\...) and Unix paths (/home/user/...) with [REDACTED_PATH].

3. First version of the Unix pattern was too greedy (matched on any single slash), incorrectly redacting things like "3/4" and parts of URLs. Fixed by requiring at least two slashes, so it only 
matches genuine multi-segment paths.

4. Real lesson: after fixing the pattern, it still looked broken when tested in an already-open Python shell — because the shell had the OLD version of the function cached in memory from before the edit. Had to start a completely fresh shell to see the fix actually take effect. Editing a .py file doesn't automatically update code already imported into a running shell session.

5. Wrote 4 pytest tests: Windows path redacted, Unix path redacted, plain text left alone, and a single slash (fraction) not mistaken for a path. All passing.

6. Decided: sanitize_paths() should NOT try to handle URLs — a plain public URL like https://example.com isn't sensitive. Credential- bearing URLs (https://user:pass@host) are a separate, later concern (sanitize_urls()), not this function's job.

--------------------------------------------------------------------------------------------------------------
Known limitations, deliberately accepted (not fixed):
   - Unix paths containing spaces (e.g. "/home/user/My Documents/file.py") 
     only get partially redacted — the pattern stops at the first space. 
     Rare in practice (error tracebacks rarely include spaced folder 
     names), and handling arbitrary spaces risks new false positives 
     elsewhere. Accepted as a known gap rather than over-engineering the regex.
   - Windows paths using forward slashes (C:/Users/...) leave the drive 
     letter (C:) visible, since the rest gets caught by the Unix path 
     pattern instead. Minor leak (a bare drive letter isn't very 
     sensitive on its own) — accepted rather than adding complexity.
----------------------------------------------------------------------------------------------------------------

7. Deliberately tried to break the sanitizer with adversarial inputs: paths with spaces, emails with +, tokens at exact length boundaries, multiple emails, quoted env var values, forward-slash Windows paths.

8. Found 2 new limitations, documented rather than fixed (over-engineering the regex risks new false positives elsewhere):
- Paths containing spaces only get partially redacted.
- Windows paths with forward slashes (C:/Users/...) leave the drive letter visible.

9. Wired sanitize() into dmrun.py: message is sanitized BEFORE fingerprinting, right after parse_error(). Reasoning: fingerprinting the sanitized version means the fingerprint reflects the meaningful error content, not incidental sensitive details like a username in a path — and guarantees nothing sensitive ever reaches the fingerprint, debounce state file, or the server.

10. Verified end-to-end with a fake API key in a test script: confirmed via a temporary debug print that the SANITIZED message (with [REDACTED_TOKEN]) is what actually gets fingerprinted and sent — not the raw text. Removed the debug print after confirming.

11. Built local_service/settings.py: load_settings()/save_settings() reading/writing settings.json. Defaults to {privacy_mode: local_only, confidence_threshold: 0.6}. Auto-creates the file with defaults on first run if it doesn't exist yet. Gitignored, since it's a runtime-generated, user-specific config file.

Week 5 — Risk Scorer, Dataset Growth

1. Wrote assess_risk() and 3 tests — all passing in isolation.

2. Found a real gap during a full-project audit: assess_risk() was never actually wired into dmrun.py, despite being discussed and written earlier — the import and the "review" branch were simply missing from the real file. Fixed by adding the risk check right after sanitize(), before fingerprinting: if "review", skip fingerprinting, debounce, and the POST entirely, and report locally.

3. Verified live: a string that survives sanitize() (18 chars, under the 20-char token threshold) but exceeds assess_risk()'s 16-char threshold correctly gets blocked, with no POST reaching the server — confirmed via the uvicorn log showing no new request.

4. Lesson: "we discussed this and I wrote the code" isn't the same as "it's actually in the file." A full audit against the actual plan text caught this before it became a real problem.

#### flagging : 
key_error is naturally harder to classify from message text alone, since KeyError messages are inherently terse.
(short, low-context messages)


1. Wrote a generate_rows() helper: runs a code snippet as a subprocess, captures and sanitizes the resulting error message, returns a labeled row (or nothing if the snippet didn't actually error).

2. Generated 12-13 examples each for key_error, index_error, type_error, none_type_error, syntax_error, and attribute_error.

3. Real findings from the data itself:
   - key_error messages are just the missing key name — no shared structure across examples, since Python's KeyError message is inherently terse. Likely the hardest category to learn from text alone.
   - index_error always produces the exact same message ("list index out of range") regardless of the code — easiest category to learn.
   - none_type_error messages reliably contain the literal word "NoneType" — this is exactly the signal the ML classifier can use that the rules-based exception-name mapping can't see, since it only looks at the exception class name, not the message text.
   - type_error and none_type_error share overlapping message wording (e.g. "unsupported operand type(s) for +: 'NoneType' and 'int'") — likely to be a genuinely confusable pair in the confusion matrix.

Week 5 — Dataset Finalization 

1. Generated remaining categories (module_not_found, file_not_found, value_error) with 5-6 snippets each, rather than forcing 12 — since these categories still have real but limited natural variety.

2. Decided NOT to generate more examples for permission_error, network_error, and other_error — tested this empirically (tried a permission_error variant via a different code path, got the exact same message as the original) rather than assuming. These categories don't have meaningful message diversity to capture; padding them would just recreate the redundancy problem already fixed elsewhere.

3. Hit a real Jupyter pitfall: re-ran a "load CSV -> concat -> save" cell twice, which doubled several rows since it read the ALREADY-UPDATED file on the second run and appended the same in-memory rows again. Fixed surgically by deduplicating only the affected categories, preserving the deliberately-kept duplicate caps elsewhere. Lesson: cells with file read+write side effects are dangerous to re-run blindly in a notebook — need to track which cells are "already applied" versus safe to re-run.

Final dataset: 85 rows across 12 categories, with counts genuinely reflecting each category's real message diversity (3 for index_error, 13 for type_error) rather than an artificial uniform target.

Week 5 — Notebook Cleanup and Final Dataset (continued)

1. Notebook had become hard to trust after many rounds of patches, re-runs, and accidental double-merges. Rebuilt it cleanly from scratch: renamed the old one to _scratch for reference, wrote a new notebook containing only the final, correct, working cells in clear order (path fix, imports, snippet lists, generation, trim, save, chart, split).

2. Confirmed via the clean rebuild that permission_error and other_error (both at 2 examples) were the two categories missing from the test set — a real, reproducible structural issue, not a one-off fluke from the earlier messy notebook.

3. Added 1-3 more examples to network_error, permission_error, and other_error specifically to make them reliably evaluable. Confirmed all 12 categories now appear in both train and test sets after the stratified split.

Week 5 — Model Training

1. Vectorized training data with TfidfVectorizer (max_features=5000, ngram_range=(1,2)). Trained Logistic Regression: macro F1 = 0.86, accuracy = 0.89.

2. Trained Linear SVM for comparison: macro F1 = 0.77, accuracy = 0.78 — worse across the board. Likely because with only ~70 training examples across 12 categories, there isn't enough data yet for SVM's decision-boundary approach to have an advantage over Logistic Regression's probability-based approach.

3. Confusion matrix revealed two real, explainable weaknesses:
   - other_error never gets predicted at all — its lone test example 
     got misclassified as key_error. Makes sense given it's a 
     deliberate catch-all with almost no consistent training signal.
   - type_error and none_type_error get confused with each other once, 
     due to genuinely overlapping training vocabulary ("NoneType" 
     appearing in both categories' messages).

4. Chose Logistic Regression as the primary model based on the comparison numbers.

5. Wrote ml_engine/train.py: a standalone script reproducing the full pipeline (load -> split -> vectorize -> train -> evaluate -> save). Verified genuine reproducibility by deleting the saved joblib files and re-running the script — it recreated them, with the classification report output byte-for-byte identical to the notebook's original run, confirming random_state=42 makes the whole pipeline deterministic.

Week 6 — Cross-validation and its outcome

Single 80/20 splits gave inconsistent macro F1 (0.86, 0.92, 0.82) because most categories have only 1-3 test examples, so one flipped prediction swings the score by 5-10 points. Ran 3-fold stratified cross-validation instead: every row gets predicted exactly once by a model that never saw it, giving a stable score across all 96 rows.

Result: macro F1 = 0.807. other_error scored 0.00 across all 8 examples, tested this time, not a single unlucky split. Its 8 examples are unrelated sentences with no shared vocabulary, so TF-IDF has nothing consistent to learn. type_error (0.55) and none_type_error (0.73) remain confused with each other, as expected from their "NoneType" vocabulary.

Decision: 0.807 is the reported macro F1, not the higher single-split numbers seen earlier. Single splits on a dataset this small are not reliable enough to report on their own.

#### Fixing key_error and other_error with error_type

Root cause: key_error's message is always a single unrelated word (the missing key). other_error's messages were 14 completely unrelated sentences from different exception types. Neither had any consistent vocabulary across its own examples, so TF-IDF had nothing to learn regardless of how many examples were added.

The message alone was never going to be enough for these categories. parse_error() already extracts error_type separately, but the classifier was only ever given message. Changed the training text to "{error_type} {message}" instead of message alone.

Result: key_error went from F1 0.00 to 1.00. other_error went from 0.00 to 0.90. Macro F1 (3-fold CV) rose from 0.807 to 0.925, same evaluation method both times.

type_error (0.63) and none_type_error (0.73) are still confused with each other: both share error_type "TypeError",so including the type doesn't help distinguish them. This is the one remaining confusion that reflects a genuine ambiguity in the message text.

Decision: for live inference later, feed the classifier "{error_type} {message}", matching training. Where confidence is low (expected mainly for the type_error / none_type_error boundary), route to a confidence threshold rather than trusting the ML prediction .

## File status note (added during model switch)

Three training notebooks exist in ml_engine/notebooks/:training_and_evaluation_scratch.ipynb and training_and_evaluation_scratch2.ipynb are archived history only, both now have a guard cell that raises an error if run, to prevent accidentally overwriting current data with stale output.

training_and_evaluation.ipynb is the single current, authoritative notebook. It and ml_engine/train.py are the only things that should ever write to dataset.csv, classifier.joblib, or vectorizer.joblib. As long as that stays true, whatever those three files currently contain on disk is correct by construction — there is no other writer.

Current model: Linear SVM wrapped in CalibratedClassifierCV, trained on a 132-row dataset. Chosen over Logistic Regression after dataset expansion widened the performance gap to 0.957 vs 0.801 macro F1 (3-fold CV). See Model Comparison and Decision section in the notebook for full reasoning.

Week 6 — ML classifier wired into the live pipeline

Added confidence-threshold routing to /analyze: the ML model (loaded 
via classifier_service.py) always runs first; if its confidence meets 
or exceeds settings.json's confidence_threshold (0.6), its category is 
used (source: "ml"). Otherwise, falls back to the existing 
normalize_error_type() rules mapping (source: "rules").

Verified two real cases:
1. Known-but-ambiguous: TypeError with 'NoneType' in the message, confidence 0.54 — correctly fell below threshold, routed to rules, matching the rules engine's existing correct behavior for this case.
2. Unknown to both systems: ConnectionResetError, confidence 0.55 — the ML model and the rules engine independently agreed on other_error via two different mechanisms (low similarity to any trained category vs. the rules engine's explicit default), without coordinating with each other.

/latest and /analyze responses now include confidence and source. 
Confirmed the widget handles the updated response shape correctly 
with no changes needed.