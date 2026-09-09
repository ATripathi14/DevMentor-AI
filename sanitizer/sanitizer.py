import re


def sanitize_paths(text: str) -> str:
    """Replaces Windows and Unix file paths in text with [REDACTED_PATH].

    Windows paths look like: C:\\Users\\apurv\\secret.py
    Unix paths look like: /home/user/secret.py

    Requires at least two slashes for Unix-style paths, so ordinary text
    containing a single slash (e.g. "3/4", "and/or") is not mistakenly
    treated as a file path.
    """
    # Windows paths: a drive letter, colon, backslash, then the rest of the path.
    text = re.sub(r"[A-Za-z]:\\[^\s]+", "[REDACTED_PATH]", text)

    # Unix paths: at least two "/segment" groups in a row, including
    # filenames with extensions (the "." is included so "secret.py"
    # isn't split into "secret" + a dangling ".py").
    text = re.sub(r"/[\w./]+/[\w./]+", "[REDACTED_PATH]", text)

    return text