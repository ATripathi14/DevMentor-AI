import sys
from runner import get_output_error, parse_error, fingerprint, should_notify

if __name__ == "__main__":
    args = sys.argv[1:]

    # it makes sure the user actually gave both pieces that are needed — the interpreter name and the script path. If they didn't, it exits with the 'Usage' message.
    if len(args) < 2:
        print("Usage: python dmrun.py python <script_path>")
        sys.exit(1)

    script_path = args[-1]  # the script is always the last argument
    error = get_output_error(script_path)  # capture the error if any

    if error:
        result = parse_error(error)  # pull out just the error type + message
        if result:
            error_type, message = result
            fingerprint_id = fingerprint(error_type, message)  # unique ID for this specific error

            if should_notify(fingerprint_id):
                print(f"{error_type}: {message}")
                print(f"[fingerprint: {fingerprint_id}]")
            else:
                print(f"(suppressed — same error seen recently) {error_type}: {message}")
        else:
            print("An error occurred but could not be parsed.")
    else:
        print("Script ran successfully.")