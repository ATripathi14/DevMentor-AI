from sanitizer.sanitizer import (
    sanitize_paths, sanitize_emails, sanitize_tokens,
    sanitize_env_vars, sanitize_urls, sanitize,
)

# --- paths ---
def test_windows_path_is_redacted():
    text = r"Error in C:\Users\apurv\secret.py at line 10"
    result = sanitize_paths(text)
    assert "[REDACTED_PATH]" in result
    assert "apurv" not in result

def test_unix_path_is_redacted():
    text = "Error in /home/user/secret.py at line 10"
    result = sanitize_paths(text)
    assert "[REDACTED_PATH]" in result
    assert "secret.py" not in result

def test_plain_text_is_not_modified():
    text = "This is just a normal sentence with no paths."
    assert sanitize_paths(text) == text

def test_single_slash_is_not_mistaken_for_a_path():
    text = "The fraction 3/4 is not a file path."
    assert sanitize_paths(text) == text

def test_paths_regex_does_not_eat_urls():
    text = "Visit https://internal-api.com/status for info"
    result = sanitize_paths(text)
    assert "https://" in result

# --- emails ---
def test_email_is_redacted():
    text = "Contact us at john.doe@example.com for help."
    result = sanitize_emails(text)
    assert "[REDACTED_EMAIL]" in result
    assert "john.doe" not in result

def test_text_without_email_is_not_modified():
    text = "This has no email in it."
    assert sanitize_emails(text) == text

# --- tokens ---
def test_long_token_is_redacted():
    text = "My key is sk_live_51H8xK2eZ9mFq3RtY7pL for the API."
    result = sanitize_tokens(text)
    assert "[REDACTED_TOKEN]" in result
    assert "sk_live_51H8xK2eZ9mFq3RtY7pL" not in result

def test_short_word_is_not_mistaken_for_a_token():
    text = "This is a short word, not a token."
    assert sanitize_tokens(text) == text

# --- env vars ---
def test_env_var_value_is_redacted():
    text = "export SECRET_KEY=abc123def456"
    result = sanitize_env_vars(text)
    assert "[REDACTED_VALUE]" in result
    assert "abc123def456" not in result
    assert "SECRET_KEY=" in result

def test_text_without_env_var_is_not_modified():
    text = "Just a normal sentence with no assignments."
    assert sanitize_env_vars(text) == text

# --- urls ---
def test_url_credentials_are_redacted():
    text = "Connect to https://admin:hunter2pass@internal-api.com now"
    result = sanitize_urls(text)
    assert "[REDACTED_CREDENTIALS]" in result
    assert "hunter2pass" not in result
    assert "internal-api.com" in result

def test_url_without_credentials_is_not_modified():
    text = "Visit https://example.com/docs for help."
    assert sanitize_urls(text) == text


def test_bare_url_without_credentials_is_not_treated_as_a_path():
    """A URL with no embedded credentials should survive sanitize_paths untouched."""
    text = "See https://example.com/path for details"
    result = sanitize_paths(text)
    assert result == text


def test_long_identifier_is_still_caught_as_a_token():
    """Document the trade-off: any 20+ char identifier gets redacted, not just real secrets."""
    text = "variable name: normal-long-identifier"
    result = sanitize_tokens(text)
    assert "[REDACTED_TOKEN]" in result

# --- master sanitize() ---
def test_sanitize_chains_all_five():
    text = (
        "Error in /home/user/secret.py — contact john.doe@example.com. "
        "Key: sk_live_51H8xK2eZ9mFq3RtY7pL. export SECRET_KEY=abc123def456. "
        "URL: https://admin:hunter2pass@internal-api.com"
    )
    result = sanitize(text)
    assert "[REDACTED_PATH]" in result
    assert "[REDACTED_EMAIL]" in result
    assert "[REDACTED_VALUE]" in result
    assert "[REDACTED_TOKEN]" in result or "[REDACTED_CREDENTIALS]" in result
    assert "secret.py" not in result
    assert "john.doe" not in result
    assert "abc123def456" not in result
    assert "hunter2pass" not in result