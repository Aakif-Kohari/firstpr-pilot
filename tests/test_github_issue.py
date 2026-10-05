import pytest
import requests

from firstpr_pilot import github_issue
from firstpr_pilot.github_issue import GitHubError, fetch_github_issue


class Resp:
    def __init__(self, status, data=None):
        self.status_code, self.data = status, data or {}
        self.ok = status < 400

    def json(self):
        return self.data


def test_fetch_ok(monkeypatch):
    monkeypatch.setattr(github_issue.requests, "get", lambda *a, **k: Resp(200, {"title": "T"}))
    assert fetch_github_issue("o", "r", 1)["title"] == "T"


@pytest.mark.parametrize("status,match", [(404, "not found"), (403, "rate limit"), (429, "rate limit"), (500, "HTTP 500")])
def test_fetch_errors(monkeypatch, status, match):
    monkeypatch.setattr(github_issue.requests, "get", lambda *a, **k: Resp(status))
    with pytest.raises(GitHubError, match=match):
        fetch_github_issue("o", "r", 1)


def test_fetch_network_error(monkeypatch):
    def boom(*a, **k):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr(github_issue.requests, "get", boom)
    with pytest.raises(GitHubError, match="Could not reach"):
        fetch_github_issue("o", "r", 1)


def test_token_header(monkeypatch):
    seen = {}

    def fake_get(url, headers, timeout):
        seen.update(headers)
        return Resp(200, {})

    monkeypatch.setattr(github_issue.requests, "get", fake_get)
    fetch_github_issue("o", "r", 1, token="abc")
    assert seen["Authorization"] == "Bearer abc"
