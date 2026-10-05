"""Fetch public GitHub issues through the REST API."""

from __future__ import annotations

import os
import re

import requests

ISSUE_URL_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/issues/(\d+)(?:[/?#].*)?$"
)


class GitHubError(Exception):
    """Raised when an issue cannot be fetched."""


def parse_github_url(url: str | None) -> tuple[str, str, int] | None:
    """Parse a GitHub issue URL into (owner, repo, issue_number), or None if invalid."""
    if not url:
        return None
    match = ISSUE_URL_RE.match(url.strip())
    if not match:
        return None
    return match.group(1), match.group(2), int(match.group(3))


def fetch_github_issue(
    owner: str, repo: str, issue_number: int, token: str | None = None, timeout: int = 10
) -> dict:
    """Fetch an issue from the GitHub REST API (token optional, raises higher rate limits)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "firstpr-pilot"}
    token = token or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as exc:
        raise GitHubError(f"Could not reach GitHub: {exc}") from exc

    if response.status_code == 404:
        raise GitHubError("Issue not found. Check the URL and make sure the repository is public.")
    if response.status_code in (403, 429):
        raise GitHubError(
            "GitHub rate limit reached. Wait a few minutes or set GITHUB_TOKEN for a higher limit."
        )
    if not response.ok:
        raise GitHubError(f"GitHub returned HTTP {response.status_code}.")
    return response.json()
