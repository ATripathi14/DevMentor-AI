# subprocess module allows you to spawn new processes, connect to their input/output/error pipes, 
# and obtain their return codes

import sys
import subprocess
import hashlib

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
    #Return a short, stable hash identifying this error
    text = f"{error_type}:{message}"
    return hashlib.sha256(text.encode()).hexdigest()[:12]

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

