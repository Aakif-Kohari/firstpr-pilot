#!/usr/bin/env python3
"""Fetch a public GitHub issue and print its title and body as JSON.

Usage: python fetch_issue.py https://github.com/<owner>/<repo>/issues/<number>
Standard library only. Set GITHUB_TOKEN for a higher rate limit.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

PATTERN = re.compile(r"^https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/issues/(\d+)")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: fetch_issue.py <github-issue-url>", file=sys.stderr)
        return 2
    match = PATTERN.match(sys.argv[1].strip())
    if not match:
        print("Not a GitHub issue URL.", file=sys.stderr)
        return 2
    owner, repo, number = match.groups()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{number}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "firstpr-pilot-skill"},
    )
    token = os.getenv("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        print(f"GitHub returned HTTP {exc.code}.", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Could not reach GitHub: {exc.reason}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "title": data.get("title"),
                "state": data.get("state"),
                "labels": [label["name"] for label in data.get("labels", [])],
                "body": data.get("body") or "",
                "url": data.get("html_url"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
