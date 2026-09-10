import re

def sanitize_paths(text: str) -> str:
    """Redact file paths (Windows and Unix) so usernames/folders don't leak."""
    text = re.sub(r"[A-Za-z]:\\[^\s]+", "[REDACTED_PATH]", text)
    # (?<!/) skips a slash that's part of "//" (i.e. a URL scheme) — must run after sanitize_urls
    text = re.sub(r"(?<!/)/[\w.]+(?:/[\w.]+)+", "[REDACTED_PATH]", text)
    return text


def sanitize_emails(text: str) -> str:
    """Redact email addresses."""
    return re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[REDACTED_EMAIL]", text)


def sanitize_tokens(text: str) -> str:
    """Redact long alphanumeric strings (likely API keys/tokens)."""
    return re.sub(r"\b[A-Za-z0-9_-]{20,}\b", "[REDACTED_TOKEN]", text)


def sanitize_env_vars(text: str) -> str:
    """Redact the VALUE in KEY=VALUE assignments, keep the key name visible."""
    return re.sub(r"([A-Z_][A-Z0-9_]*=)\S+", r"\1[REDACTED_VALUE]", text)


def sanitize_urls(text: str) -> str:
    """Redact user:password@ credentials embedded in a URL. Must run first in sanitize()."""
    pattern = r"(https?://)([^:/@\s]+):([^@\s]+)@"
    return re.sub(pattern, r"\1[REDACTED_CREDENTIALS]@", text)


def sanitize(text: str) -> str:
    """Run all sanitizers in order. URLs first, paths last — order avoids one regex eating another's target."""
    text = sanitize_urls(text)
    text = sanitize_emails(text)
    text = sanitize_tokens(text)
    text = sanitize_env_vars(text)
    text = sanitize_paths(text)
    return text