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


7. Deliberately tried to break the sanitizer with adversarial inputs: paths with spaces, emails with +, tokens at exact length boundaries, multiple emails, quoted env var values, forward-slash Windows paths.

8. Found 2 new limitations, documented rather than fixed (over-engineering the regex risks new false positives elsewhere):
- Paths containing spaces only get partially redacted.
- Windows paths with forward slashes (C:/Users/...) leave the drive letter visible.

9. Wired sanitize() into dmrun.py: message is sanitized BEFORE fingerprinting, right after parse_error(). Reasoning: fingerprinting the sanitized version means the fingerprint reflects the meaningful error content, not incidental sensitive details like a username in a path — and guarantees nothing sensitive ever reaches the fingerprint, debounce state file, or the server.

10. Verified end-to-end with a fake API key in a test script: confirmed via a temporary debug print that the SANITIZED message (with [REDACTED_TOKEN]) is what actually gets fingerprinted and sent — not the raw text. Removed the debug print after confirming.