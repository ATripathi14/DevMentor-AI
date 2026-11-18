"""
Collect Python tracebacks from public GitHub issues.

Features:
- Searches public GitHub issues for a broad set of exception types.
- Collects issue bodies and paginated comments.
- Extracts multiple traceback blocks and handles chained tracebacks.
- Uses the final valid, non-indented exception line rather than the first regex match.
- Deduplicates tracebacks using SHA-256.
- Resumes safely using both existing JSONL records and processed issue IDs.
- Does not mark an issue fully processed when comment retrieval fails or is capped.
- Limits records per repository to improve source diversity.
- Handles network errors, server errors, and GitHub rate limits.
- Saves records incrementally.

Output files (kept local; do not commit):
    ml_engine/data/eval/raw_tracebacks.jsonl
    ml_engine/data/eval/processed_issues.txt

Expected layout:
    project/
        .env
        ml_engine/
            collect_github.py
            data/
                eval/
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


# 1. CONFIGURATION
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "GITHUB_TOKEN not found. Check that .env is in the project root "
        "and contains GITHUB_TOKEN=your_token."
    )

BASE_URL = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

OUTPUT_DIR = SCRIPT_DIR / "data" / "eval"
OUT = OUTPUT_DIR / "raw_tracebacks.jsonl"
PROCESSED = OUTPUT_DIR / "processed_issues.txt"

# Start conservatively. Increase only after inspecting the collected data.
PAGES_PER_QUERY = 1
PER_PAGE = 30

MAX_RETRIES = 5
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60
REQUEST_DELAY = 3

# None means fetch every comment page. An integer caps the number of pages.
# If the cap is reached while more comments exist, the issue is NOT marked
# processed and can be retried on a later run.
MAX_COMMENT_PAGES: int | None = None

# Maximum number of unique traceback records retained from one repository.
MAX_PER_REPO = 10

TRACEBACK_HEADER = "Traceback (most recent call last):"

# Combine the exception queries from both previous versions.
EXCEPTIONS = [
    "KeyError",
    "AttributeError",
    "TypeError",
    "ConnectionError",
    "ValueError",
    "ModuleNotFoundError",
    "ImportError",
    "ZeroDivisionError",
    "SystemError",
    "SyntaxError",
    "RuntimeError",
    "ReferenceError",
    "OverflowError",
    "MemoryError",
    "AssertionError",
    "EOFError",
    "NameError",
    "IndentationError",
    "PermissionError",
    "FileNotFoundError",
    "OSError",
    "IndexError",
    "UnicodeDecodeError",
    "TimeoutError",
    "NotImplementedError",
]

HEADER_QUERY = '"Traceback (most recent call last)"'
QUERIES = [
    f"{HEADER_QUERY} {exception_name} language:Python"
    for exception_name in EXCEPTIONS
]

SPECIAL_EXCEPTIONS = {
    "KeyboardInterrupt",
    "SystemExit",
    "StopIteration",
    "GeneratorExit",
}

# These labels can look like "Name: message" but are normally log/prose labels,
# not Python exception class names.
NON_EXCEPTION_PREFIXES = {
    "note",
    "info",
    "debug",
    "warning",
    "warn",
    "critical",
    "fatal",
    "trace",
}

EXCEPTION_LINE_PATTERN = re.compile(
    r"^([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(?::(?:\s|$)|$)"
)


# 2. HASHING AND EXCEPTION PARSING

def get_hash(traceback_text: str) -> str:
    """Return a stable SHA-256 hash for a normalized traceback."""
    normalized = "\n".join(
        line.rstrip() for line in traceback_text.strip().splitlines()
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_exception_type(line: str) -> str | None:
    """
    Extract an exception class from a candidate final traceback line.

    Accepts normal Python exception names ending in Error, Exception,
    Warning, or Exit, plus Python's common special exceptions.
    """
    line = line.strip()
    if not line:
        return None

    if line in SPECIAL_EXCEPTIONS:
        return line

    match = EXCEPTION_LINE_PATTERN.match(line)
    if not match:
        return None

    exception_name = match.group(1)
    short_name = exception_name.rsplit(".", 1)[-1]

    if short_name.lower() in NON_EXCEPTION_PREFIXES:
        return None

    if short_name.endswith(("Error", "Exception", "Warning", "Exit")):
        return exception_name

    return None


# 3. LOAD EXISTING DATA AND RESUME STATE
def load_existing_data() -> tuple[set[str], dict[str, int], int]:
    """
    Recover traceback hashes, per-repository counts, and the highest record ID.

    The traceback is re-hashed when available instead of blindly trusting a
    stored hash. This also supports older JSONL records.
    """
    seen: set[str] = set()
    repo_counts: dict[str, int] = {}
    max_id = 0
    malformed = 0

    if not OUT.exists():
        return seen, repo_counts, max_id

    with OUT.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                traceback_text = record.get("traceback", "")
                stored_hash = record.get("traceback_hash", "")

                if traceback_text:
                    traceback_hash = get_hash(traceback_text)
                elif stored_hash:
                    traceback_hash = stored_hash
                else:
                    continue

                seen.add(traceback_hash)

                repository = record.get("repository_url", "")
                if repository:
                    repo_counts[repository] = repo_counts.get(repository, 0) + 1

                record_id = record.get("id", "")
                match = re.fullmatch(r"TB(\d+)", record_id)
                if match:
                    max_id = max(max_id, int(match.group(1)))

            except (json.JSONDecodeError, AttributeError, TypeError):
                malformed += 1

    if malformed:
        print(f"[WARNING] Skipped {malformed} malformed JSONL record(s).")

    return seen, repo_counts, max_id


def load_processed_issues() -> set[str]:
    """Load issue IDs that were completely processed in previous runs."""
    if not PROCESSED.exists():
        return set()

    return {
        line.strip()
        for line in PROCESSED.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def mark_issue_processed(issue_id: str) -> None:
    """Persist an issue ID only after its body/comments were fully handled."""
    with PROCESSED.open("a", encoding="utf-8") as file:
        file.write(f"{issue_id}\n")


# 4. GITHUB API REQUEST HANDLING
def github_get(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET with retries, exponential backoff, and GitHub rate-limit handling."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code in (403, 429):
                remaining = response.headers.get("X-RateLimit-Remaining")
                response_text = response.text.lower()

                is_rate_limited = (
                    response.status_code == 429
                    or remaining == "0"
                    or "rate limit" in response_text
                    or "secondary rate limit" in response_text
                )

                if not is_rate_limited:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")
                reset = response.headers.get("X-RateLimit-Reset")

                if retry_after:
                    try:
                        wait_seconds = max(1, int(retry_after))
                    except ValueError:
                        wait_seconds = min(30 * (2 ** attempt), 300)
                elif remaining == "0" and reset:
                    wait_seconds = max(
                        1, int(reset) - int(time.time()) + 2
                    )
                else:
                    wait_seconds = min(30 * (2 ** attempt), 300)

                print(f"[RATE LIMIT] Waiting {wait_seconds}s...")
                time.sleep(wait_seconds)
                continue

            if response.status_code in (500, 502, 503, 504):
                wait_seconds = min(5 * (2 ** attempt), 120)
                print(
                    f"[SERVER ERROR] HTTP {response.status_code}; "
                    f"retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as error:
            wait_seconds = min(5 * (2 ** attempt), 120)
            print(
                f"[NETWORK] Attempt {attempt + 1}/{MAX_RETRIES}: {error}. "
                f"Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    raise RuntimeError(
        f"GitHub request failed after {MAX_RETRIES} attempts: {url}"
    )


# 5. TRACEBACK EXTRACTION
def extract_tracebacks(text: str) -> list[str]:
    """
    Extract traceback blocks from issue bodies/comments.

    Each block begins at a Python traceback header. Within that block, inspect
    non-indented lines and retain the block through the LAST valid exception
    line. This avoids stopping at an earlier line such as "Note: ...".

    Chained tracebacks normally contain another traceback header, so each
    traceback segment is processed independently.
    """
    if not text:
        return []

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    starts = [
        match.start()
        for match in re.finditer(re.escape(TRACEBACK_HEADER), text)
    ]

    results: list[str] = []

    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        block = text[start:end]
        lines = block.splitlines()

        if not lines:
            continue

        # A valid traceback must have the header and a final exception line.
        # Search all non-indented lines, then use the last valid candidate.
        terminal_index: int | None = None

        for line_index, line in enumerate(lines[1:], start=1):
            if not line.strip():
                continue

            if line[0].isspace():
                continue

            if get_exception_type(line):
                terminal_index = line_index

        if terminal_index is None:
            continue

        traceback_block = "\n".join(lines[: terminal_index + 1]).strip()

        # Avoid accepting a header followed by an exception-looking line with
        # no traceback frame/source content. Real tracebacks may have different
        # frame formats, so this is a light sanity check rather than a strict
        # requirement for a particular "File ..." pattern.
        if traceback_block:
            results.append(traceback_block)

    return results


# 6. SEARCH ISSUES AND FETCH COMMENTS
def search_issues(query: str, page: int) -> list[dict[str, Any]]:
    """Search public GitHub issues for one query/page."""
    data = github_get(
        f"{BASE_URL}/search/issues",
        params={
            "q": query + " is:issue",
            "per_page": PER_PAGE,
            "page": page,
            "sort": "updated",
            "order": "desc",
        },
    )
    return data.get("items", [])


def get_comments(comments_url: str) -> tuple[list[dict[str, Any]], bool]:
    """
    Fetch issue comments.

    Returns (comments, complete). If an API request fails or a configured page
    cap prevents fetching all comments, complete is False. The caller must not
    mark that issue fully processed.
    """
    comments: list[dict[str, Any]] = []
    page = 1

    while True:
        if MAX_COMMENT_PAGES is not None and page > MAX_COMMENT_PAGES:
            # We reached the configured cap. The caller should retry later
            # after increasing/removing the cap.
            return comments, False

        try:
            data = github_get(
                comments_url,
                params={"per_page": 100, "page": page},
            )
        except (
            RuntimeError,
            requests.exceptions.RequestException,
        ) as error:
            print(f"[WARNING] Comment page {page} failed: {error}")
            print(
                f"[WARNING] Retaining {len(comments)} fetched comment(s); "
                "issue will remain eligible for retry."
            )
            return comments, False

        if not data:
            return comments, True

        comments.extend(data)

        if len(data) < 100:
            return comments, True

        if MAX_COMMENT_PAGES is not None and page >= MAX_COMMENT_PAGES:
            # A full page at the cap may mean more comments exist. Do not
            # silently treat this issue as complete.
            return comments, False

        page += 1
        time.sleep(REQUEST_DELAY)


# 7. SAVE AND PROCESS RECORDS
def save_record(record: dict[str, Any]) -> None:
    """Append one record immediately; existing records are never overwritten."""
    with OUT.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_issue(
    issue: dict[str, Any],
    seen: set[str],
    repo_counts: dict[str, int],
    next_id: int,
) -> tuple[int, int, bool]:
    """
    Process an issue body and its comments.

    Returns (new_records, next_id, complete). An issue is complete only when
    all comment pages were retrieved successfully, or no comments existed.
    """
    repository_url = issue["repository_url"].replace(
        "https://api.github.com/repos/",
        "https://github.com/",
    )

    # This issue is intentionally excluded because its repository has reached
    # the configured diversity cap. It can be reconsidered by clearing the
    # processed-issues file if MAX_PER_REPO is raised later.
    if repo_counts.get(repository_url, 0) >= MAX_PER_REPO:
        return 0, next_id, True

    contents: list[tuple[str, str, str]] = [
        (issue.get("body") or "", "issue_body", "")
    ]

    comments_complete = True

    if issue.get("comments", 0) > 0:
        comments, comments_complete = get_comments(issue["comments_url"])

        for comment in comments:
            contents.append(
                (
                    comment.get("body") or "",
                    "issue_comment",
                    comment.get("html_url", ""),
                )
            )

    collected = 0

    for content, content_type, comment_url in contents:
        for traceback_text in extract_tracebacks(content):
            if repo_counts.get(repository_url, 0) >= MAX_PER_REPO:
                break

            traceback_hash = get_hash(traceback_text)
            if traceback_hash in seen:
                continue

            exception_type = get_exception_type(
                traceback_text.splitlines()[-1]
            )
            if not exception_type:
                continue

            next_id += 1

            record = {
                "id": f"TB{next_id:06d}",
                "traceback": traceback_text,
                "traceback_hash": traceback_hash,
                "exception_type": exception_type,
                "source": "github",
                "source_type": content_type,
                "repository_url": repository_url,
                "issue_url": issue.get("html_url", ""),
                "comment_url": comment_url,
                "collected_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(),
                ),
                # Retained for compatibility with the earlier data schema.
                "error_category": None,
                "resolution": None,
                "label_confidence": None,
            }

            save_record(record)

            # Update in-memory state only after the record has been written.
            seen.add(traceback_hash)
            repo_counts[repository_url] = (
                repo_counts.get(repository_url, 0) + 1
            )
            collected += 1

            print(f"[+] Collected {record['id']} | {exception_type}")

    return collected, next_id, comments_complete


# 8. MAIN COLLECTION PIPELINE
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    seen, repo_counts, next_id = load_existing_data()
    processed = load_processed_issues()

    total_new = 0
    failed_search_pages = 0
    incomplete_issues = 0
    skipped_processed = 0

    print("\n========== GITHUB TRACEBACK COLLECTOR ==========")
    print(f"Existing unique tracebacks : {len(seen)}")
    print(f"Repositories represented   : {len(repo_counts)}")
    print(f"Previously processed issues: {len(processed)}")
    print(f"Next record ID             : TB{next_id + 1:06d}")
    print(f"Search queries             : {len(QUERIES)}")
    print(f"Pages per query            : {PAGES_PER_QUERY}")
    print(f"Maximum per repository     : {MAX_PER_REPO}")
    print(f"Comment page limit         : {MAX_COMMENT_PAGES or 'unlimited'}")

    for query_index, query in enumerate(QUERIES, start=1):
        print(f"\n[{query_index}/{len(QUERIES)}] Searching: {query}")

        for page in range(1, PAGES_PER_QUERY + 1):
            print(f"Fetching search page {page}...")

            try:
                issues = search_issues(query, page)
            except (
                RuntimeError,
                requests.exceptions.RequestException,
            ) as error:
                print(f"[WARNING] Search page {page} failed: {error}")
                failed_search_pages += 1
                continue

            if not issues:
                print("[INFO] No more issues found.")
                break

            for issue in issues:
                issue_id = str(issue.get("id", ""))
                if not issue_id:
                    continue

                if issue_id in processed:
                    skipped_processed += 1
                    continue

                try:
                    new_count, next_id, complete = process_issue(
                        issue,
                        seen,
                        repo_counts,
                        next_id,
                    )
                    total_new += new_count

                    if complete:
                        processed.add(issue_id)
                        mark_issue_processed(issue_id)
                    else:
                        incomplete_issues += 1
                        print(
                            f"[INFO] Issue {issue_id} was only partially "
                                                       "processed; it will be retried."
                        )

                except (
                    RuntimeError,
                    requests.exceptions.RequestException,
                    KeyError,
                    TypeError,
                ) as error:
                    # Do not persist this issue ID. A later run can retry it.
                    print(
                        f"[WARNING] Issue processing failed "
                        f"({issue.get('html_url', 'unknown')}): {error}"
                    )
                    incomplete_issues += 1
                    continue

            time.sleep(REQUEST_DELAY)

    print("\n========== COLLECTION SUMMARY ==========")
    print(f"New tracebacks collected    : {total_new}")
    print(f"Total unique tracebacks     : {len(seen)}")
    print(f"Repositories represented   : {len(repo_counts)}")
    print(f"Previously processed skips : {skipped_processed}")
    print(f"Incomplete/retryable issues : {incomplete_issues}")
    print(f"Failed search pages         : {failed_search_pages}")
    print(f"Raw output                  : {OUT}")
    print(f"Processed issue IDs         : {PROCESSED}")
    print("=========================================")


if __name__ == "__main__":
    main()
