from core.parsers import parse_any


def test_parses_python_traceback():
    raw = 'Traceback (most recent call last):\n  File "a.py", line 3, in <module>\n    d["x"]\nKeyError: \'x\''
    e = parse_any(raw)
    assert e.language == "python"
    assert e.exception_type == "KeyError"
    assert e.message == "'x'"
    assert len(e.frames) == 1


def test_short_type_strips_module():
    raw = "Traceback (most recent call last):\n  File \"a.py\", line 1\nurllib3.exceptions.MaxRetryError: boom"
    assert parse_any(raw).short_type == "MaxRetryError"


def test_text_matches_model_input_format():
    raw = "Traceback (most recent call last):\n  File \"a.py\", line 1\nValueError: bad"
    assert parse_any(raw).text == "ValueError bad"


def test_unrecognized_text_returns_none():
    assert parse_any("hello world, nothing wrong here") is None