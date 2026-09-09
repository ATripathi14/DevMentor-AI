from sanitizer.sanitizer import sanitize_paths


def test_windows_path_is_redacted():
    """A Windows-style path should be replaced with [REDACTED_PATH]."""
    text = r"Error in C:\Users\apurv\secret.py at line 10"
    result = sanitize_paths(text)
    assert "[REDACTED_PATH]" in result
    assert "apurv" not in result


def test_unix_path_is_redacted():
    """A Unix-style path should be replaced with [REDACTED_PATH]."""
    text = "Error in /home/user/secret.py at line 10"
    result = sanitize_paths(text)
    assert "[REDACTED_PATH]" in result
    assert "secret.py" not in result


def test_plain_text_is_not_modified():
    """Ordinary text with no paths should be left completely unchanged."""
    text = "This is just a normal sentence with no paths."
    result = sanitize_paths(text)
    assert result == text


def test_single_slash_is_not_mistaken_for_a_path():
    """A single slash (e.g. a fraction) should not be treated as a file path."""
    text = "The fraction 3/4 is not a file path."
    result = sanitize_paths(text)
    assert result == text