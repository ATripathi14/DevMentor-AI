Day 1 — Environment + Git setup

1. Set up the devmentor conda environment , confirmed python and conda work cleanly.
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

4. Confirmed outputs: None returned correctly when a script runs successfully with no errors, and the correct stderr string returned when a script fails — tested against 3 broken scripts and 1 working script
5. Wrote parse_error(stderr_text) extracting error type and message from the final traceback line. Uses split(":", 1) to avoid breaking on messages that contain colons themselves.
6. Built client/dmrun.py — a command-line entry point that ties everything together: run python dmrun.py python   <script>, and it captures the error, parses it, and prints the result in one step.
7. Tested all 12 scripts through dmrun.py — found and fixed bugs that may have caused issues later on.


Day 4 — Fingerprinting and Debounce

- fingerprint(error_type, message): returns a short (12-char) hash uniquely and stably identifying an error.
Same inputs -> same hash, every time. Used as a compact ID instead of comparing raw error text.

- should_notify(fp, window_seconds=60): returns False if the same fingerprint was seen within the last 
window_seconds (suppress repeat notification); otherwise records the current time and returns True.

- Debounce state (fingerprint->last_seen_timestamp) is persisted to client/.debounce_state.json instead of an in-memory dict.  Reason: dmrun.py exits after every run , so an in-memory dict would reset to empty each invocation, making debounce 
never actually suppress anything across separate runs. Persisting to disk lets state survive between runs.

- .debounce_state.json is auto-created on first write, never created manually, and is gitignored 
(runtime-generated, not source).