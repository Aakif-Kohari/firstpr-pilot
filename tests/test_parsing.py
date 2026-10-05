import pytest

from firstpr_pilot.github_issue import parse_github_url
from firstpr_pilot.prompts import (
    NO_TEXT_PROMPT,
    SYSTEM_INSTRUCTION,
    build_safety_prompt,
    build_user_prompt,
    extract_section,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/microsoft/vscode/issues/12345", ("microsoft", "vscode", 12345)),
        ("http://github.com/owner/repo/issues/1", ("owner", "repo", 1)),
        ("https://www.github.com/a/b.c/issues/7#issuecomment-9", ("a", "b.c", 7)),
        ("  https://github.com/o/r/issues/5?x=1  ", ("o", "r", 5)),
    ],
)
def test_parse_valid(url, expected):
    assert parse_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    ["https://google.com", "https://github.com/o/r/pull/1", "https://github.com/o/r/issues/", "not a url", "", None],
)
def test_parse_invalid(url):
    assert parse_github_url(url) is None


def test_prompt_with_issue_and_text():
    prompt = build_user_prompt("my logs", {"title": "Crash", "body": "It crashes"})
    assert "Crash" in prompt and "It crashes" in prompt and "my logs" in prompt


def test_prompt_handles_none_body():
    prompt = build_user_prompt(None, {"title": "T", "body": None})
    assert "None" not in prompt and "no description" in prompt


def test_prompt_truncates_long_body():
    prompt = build_user_prompt("", {"title": "T", "body": "x" * 50000})
    assert "[truncated]" in prompt and len(prompt) < 7000


def test_prompt_empty_falls_back_to_screenshot_prompt():
    assert build_user_prompt("   ", None) == NO_TEXT_PROMPT


def test_safety_prompt_contains_commands():
    assert "git push origin main" in build_safety_prompt("git push origin main")


def test_system_instruction_lists_all_sections():
    for title in ("Git Commands", "Draft PR Description", "Plain-English Explanation"):
        assert f"## {title}" in SYSTEM_INSTRUCTION


SAMPLE = """## Plain-English Explanation
It breaks.

## Git Commands
```bash
git checkout -b fix/thing
```

## Draft Commit Message
fix: thing
"""


def test_extract_section_basic():
    out = extract_section(SAMPLE, "Git Commands")
    assert out is not None and "git checkout -b fix/thing" in out and "Draft Commit" not in out


def test_extract_section_variants():
    assert extract_section("### 4. Git Commands\nls\n", "Git Commands") == "ls"
    assert extract_section("## **Git Commands**\nls\n## Next\nx", "Git Commands") == "ls"
    assert extract_section("## git commands:\nls", "Git Commands") == "ls"


def test_extract_section_missing_or_empty():
    assert extract_section(SAMPLE, "Nope") is None
    assert extract_section("", "Git Commands") is None
    assert extract_section("## Git Commands\n\n## Next\nx", "Git Commands") is None
