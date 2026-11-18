from client import hook


def test_report_posts_sanitized_payload(monkeypatch):
    sent = {}
    monkeypatch.setattr(hook, "should_notify", lambda fp: True)
    monkeypatch.setattr(hook.requests, "post", lambda url, json, timeout: sent.update(json))
    hook.report('Traceback (most recent call last):\n  File "a.py", line 1\n'
                'KeyError: \'user@example.com\'')
    assert sent["error_type"] == "KeyError"
    assert "user@example.com" not in sent["message"]


def test_report_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("service down")
    monkeypatch.setattr(hook, "should_notify", lambda fp: True)
    monkeypatch.setattr(hook.requests, "post", boom)
    hook.report('Traceback (most recent call last):\n  File "a.py", line 1\nValueError: bad')