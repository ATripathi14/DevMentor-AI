# subprocess module allows you to spawn new processes, connect to their input/output/error pipes, 
# and obtain their return codes

import sys
import subprocess
import hashlib
import time

import json
import os

def get_output_error(script_path: str) -> str | None:
    """Runs a python script and returns the stderr (std error) if it fails, or None if it succeeds.
       The error will be returned as a string.
    """

    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

   # sys.executable guarantees the usage of the exact interpreter running this code, avoiding PATH ambiguity across multiple   installed Pythons.

    if result.returncode != 0: #it holds the exit code the subprocess finished with.
        # A return code of 0 means the script ran successfully; any non-zero value (typically 1) means it crashed or exited with an error.
        return result.stderr

    return None



def parse_error(stderr_text: str) -> tuple[str, str] | None:
    #Extracts the error type and message from the traceback string and returns (error_type, message), or None if no error

    if not stderr_text:
        return None

    lines = stderr_text.strip().splitlines()
    last_line = lines[-1]  # in python the actual exception is always the last line

    if ":" in last_line:
        error_type, message = last_line.split(":", 1)
        return error_type.strip(), message.strip()

    return None


def fingerprint(error_type: str, message: str) -> str:
    # Return a short, stable hash identifying this error
    # Same error_type + message -> always the same hash (identity check).
    text = f"{error_type}:{message}"
    return hashlib.sha256(text.encode()).hexdigest()[:12]
    # [:12] -> shorten the hash for readability/logging; still unique enough for our scale.



_DEBOUNCE_FILE = os.path.join(os.path.dirname(__file__), ".debounce_state.json")
# File lives next to runner.py regardless of where the script is run from.
# Stores: { fingerprint: last_seen_unix_timestamp }


def _load_debounce_state() -> dict:
    """Read the fingerprint -> last_seen_timestamp map from disk."""
    # Returns {} if file doesn't exist yet (i.e. first run ever).
    if not os.path.exists(_DEBOUNCE_FILE):
        return {}
    with open(_DEBOUNCE_FILE, "r") as f:
        return json.load(f)


def _save_debounce_state(state: dict) -> None:
    """Write the fingerprint -> last_seen_timestamp map to disk."""
    with open(_DEBOUNCE_FILE, "w") as f:
        json.dump(state, f)


def should_notify(fp: str, window_seconds: int = 60) -> bool:
    """Return False if this fingerprint was already notified within window_seconds."""
    state = _load_debounce_state()
    now = time.time()
    last = state.get(fp)  # None if this fingerprint was never seen before
    if last is not None and (now - last) < window_seconds:
        return False  # seen too recently -> suppress notification

    # either never seen, or enough time has passed -> notify and update timestamp
    state[fp] = now
    _save_debounce_state(state)
    return True



# This only runs the code below it when the file is executed directly — not when it's imported by another file.
if __name__ == "__main__":
    scripts = [
        "ml_engine/data/raw/type_error.py",
        "ml_engine/data/raw/key_error.py",
        "ml_engine/data/raw/index_error.py",
        "ml_engine/data/raw/None_Type_Error.py",
        "test/fixtures/_working_test.py",

    ]

    for path in scripts:
        error = get_output_error(path)
        if error:
            print(parse_error(error))
        else:
            print(f"{path}: No Error (ran successfully)")

