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

3. Re-ran all 12 broken scripts through dmrun.py to confirm today's changes hadn't broken anything from Day 3 — all 12 still produced correct output.

4. Updated README's Project Status section to accurately reflect progress (Day 5 of Phase 1 completed).

5. Wrote docs/architecture.md documenting the current, as-built pipeline (separate from the target architecture shown in README).

6. Tagged v0.1-foundation on GitHub, marking Phase 0 — Foundation as complete.

   
SUMMARY OF THE WEEK -

1. I learned how a project setup is created and managed, how git works at basic level and how you think through your plan multiple times to find the gap of what is required from the project rather than what you really want it to become .

2. I now understand the project's architecture better, including what each function is responsible for and why clear naming conventions matter.

3. Since I have hit real friction with imports I also somewhat got the idea of importing modules across a project  but i still need to learn about it more.

## Known gaps — to address during Week 5 dataset construction

- normalize_error_type() currently can't distinguish NoneType errors. They surface as TypeError 
  or AttributeError with "NoneType" in the message text, not as their own exception class — 
  so none_type_error is currently unreachable as a category output. Needs message-content checking 
  (not just exception-name lookup) to fix properly.

- RecursionError is not yet in ERROR_TYPE_TO_CATEGORY — currently falls through to the default 
  "other_error" via .get()'s fallback, which is correct behavior but not an explicit, intentional mapping yet.

- Broken script filenames in ml_engine/data/raw/ have inconsistent casing (e.g. Key_Error.py vs 
  network_Error.  py vs permission_Error.py). Worth standardizing (matching category label strings) when 
  rewriting/expanding scripts for the ML dataset.

- Zero_division_Error.py (from Day 2) intentionally maps to the "other_error" category, not a dedicated
  13th label — keeping the official label set at 12 categories as originally planned.