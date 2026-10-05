"""Prompt templates and helpers for parsing model output."""

from __future__ import annotations

import re

SECTIONS = (
    "Plain-English Explanation",
    "Likely Files/Areas",
    "Step-by-Step Fix Plan",
    "Git Commands",
    "Draft Commit Message",
    "Draft PR Description",
)

SYSTEM_INSTRUCTION = """You are a patient, encouraging, and experienced mentor for first-time open-source contributors.
Your goal is to help beginners understand a bug, plan a fix, and confidently submit their first Pull Request.
Explain concepts in plain English, define any jargon you use, and give actionable, step-by-step guidance.
When you suggest files to look at, explain why they matter. If you are unsure, say so instead of guessing.
Use placeholders like <owner>, <repo> and <branch-name> in commands and never invent URLs.
Structure your answer with exactly these Markdown headings, in this order:
## Plain-English Explanation
## Likely Files/Areas
## Step-by-Step Fix Plan
## Git Commands
## Draft Commit Message
## Draft PR Description
Put the Git Commands in a single fenced code block."""

SAFETY_SYSTEM_INSTRUCTION = "You are a strict, concise Git safety reviewer for beginners."

MAX_ISSUE_BODY_CHARS = 6000
MAX_TEXT_CHARS = 12000

NO_TEXT_PROMPT = (
    "The user provided only a screenshot. Describe what error or bug it shows, "
    "then follow the required structure to help them plan a fix."
)


def _clip(value: str, limit: int) -> str:
    value = value or ""
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"


def build_user_prompt(text: str | None, issue_data: dict | None) -> str:
    """Combine pasted notes and GitHub issue data into one prompt string."""
    parts: list[str] = []
    if issue_data:
        parts.append(f"GitHub Issue Title: {issue_data.get('title') or 'N/A'}")
        body = _clip(issue_data.get("body") or "(no description)", MAX_ISSUE_BODY_CHARS)
        parts.append(f"GitHub Issue Body:\n{body}")
    if text and text.strip():
        parts.append(f"User Notes/Logs:\n{_clip(text.strip(), MAX_TEXT_CHARS)}")
    if not parts:
        return NO_TEXT_PROMPT
    return "\n\n".join(parts)


def build_safety_prompt(git_commands: str) -> str:
    """Prompt for the second-opinion model that reviews the generated Git commands."""
    return f"""Review the Git commands below for a first-time contributor.
Flag anything risky, incorrect, or unsafe, for example:
- force pushes, or pushing directly to main/master
- pushing to the wrong remote or branch
- committing secrets, credentials, or .env files
- destructive commands such as `git reset --hard` or `git clean -fd` without a warning
- commit messages that do not follow Conventional Commits

If everything is safe, reply with exactly: "✅ Looks good. These commands are safe and follow standard practice."
Otherwise list each problem briefly and give corrected commands.

Git commands to review:
{git_commands}
"""


def extract_section(markdown: str, title: str) -> str | None:
    """Return the body of a Markdown section (## or ###, optional numbering), or None."""
    if not markdown:
        return None
    pattern = (
        r"^#{2,3}\s*(?:\d+[.)]\s*)?\**" + re.escape(title) + r"\**\s*:?\s*$"
        r"\n(.*?)(?=^#{2,3}\s|\Z)"
    )
    match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    body = match.group(1).strip()
    return body or None
