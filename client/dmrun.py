import sys
import requests

from client.runner import get_output_error, fingerprint, should_notify
from core.parsers import parse_any
from sanitizer.sanitizer import sanitize, assess_risk

if __name__ == "__main__":
    args = sys.argv[1:]

    # Needs both the interpreter name and the script path.
    if len(args) < 2:
        print("Usage: python dmrun.py python <script_path>")
        sys.exit(1)

    script_path = args[-1]  # the script is always the last argument
    error = get_output_error(script_path)  # capture the error if any

    if error:
        event = parse_any(error)  # language-agnostic parse into an ErrorEvent
        if event:
            error_type = event.exception_type or ""

            # Sanitize BEFORE fingerprinting, so the fingerprint reflects the
            # meaningful error content and nothing sensitive reaches the
            # fingerprint, debounce state, or the server.
            message = sanitize(event.message)

            # Fail closed: if anything still looks suspicious after
            # sanitization, report locally and send nothing.
            if assess_risk(message) == "review":
                print(f"{error_type}: {message}")
                print("(This error was flagged for review and was not sent to the local "
                      "service — it may still contain sensitive-looking content.)")
            else:
                fingerprint_id = fingerprint(error_type, message)

                if should_notify(fingerprint_id):
                    try:
                        response = requests.post(
                            "http://localhost:8765/analyze",
                            json={
                                "error_type": error_type,
                                "message": message,
                                "fingerprint": fingerprint_id,
                            },
                            timeout=3,
                        )
                        data = response.json()
                        print(f"[{data['category']}] {data['explanation']}")
                    except requests.exceptions.ConnectionError:
                        print(f"{error_type}: {message}")
                        print("(Could not reach the local DevMentor service — is it running? "
                              "Start it with: uvicorn local_service.main:app --reload --port 8765)")
                else:
                    print(f"(suppressed — same error seen recently) {error_type}: {message}")
        else:
            print("An error occurred but could not be parsed. Raw output:")
            print(error.strip())
    else:
        print("Script ran successfully.")