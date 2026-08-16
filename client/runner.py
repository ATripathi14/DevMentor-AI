# subprocess module allows you to spawn new processes, connect to their input/output/error pipes, 
# and obtain their return codes

import sys
import subprocess

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

# This only runs the code below it when the file is executed directly — not when it's imported by another file.
if __name__ == "__main__":  
    print(get_output_error("ml_engine/data/raw/type_error.py"))
    print(get_output_error("ml_engine/data/raw/key_error.py"))
    print(get_output_error("ml_engine/data/raw/index_error.py"))