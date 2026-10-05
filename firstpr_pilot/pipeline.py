"""Orchestration: inputs -> contribution plan -> safety review. UI-independent and testable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .backends import Backend, BackendError
from .github_issue import GitHubError, fetch_github_issue, parse_github_url
from .prompts import (
    SAFETY_SYSTEM_INSTRUCTION,
    SYSTEM_INSTRUCTION,
    build_safety_prompt,
    build_user_prompt,
    extract_section,
)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class InputError(ValueError):
    """The user's input is missing or invalid."""


@dataclass
class PlanResult:
    plan: str
    git_commands: str | None = None
    safety: str | None = None
    warnings: list[str] = field(default_factory=list)


def build_plan(
    main_backend: Backend,
    safety_backend: Backend | None,
    text: str | None = None,
    issue_url: str | None = None,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
    fetch_issue: Callable[..., dict] = fetch_github_issue,
) -> PlanResult:
    """Run the full flow. Raises InputError or BackendError for the main analysis only."""
    warnings: list[str] = []

    if image_bytes:
        if image_mime not in ALLOWED_IMAGE_TYPES:
            raise InputError("Unsupported image type. Use PNG, JPEG or WebP.")
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise InputError("Image is larger than 10 MB. Please upload a smaller screenshot.")
    else:
        image_bytes, image_mime = None, None

    issue_data = None
    if issue_url and issue_url.strip():
        parsed = parse_github_url(issue_url)
        if parsed is None:
            warnings.append(
                "That does not look like a GitHub issue URL "
                "(expected https://github.com/<owner>/<repo>/issues/<number>)."
            )
        else:
            try:
                issue_data = fetch_issue(*parsed)
            except GitHubError as exc:
                warnings.append(f"Could not fetch the issue: {exc}")

    has_text = bool(text and text.strip())
    if not (issue_data or has_text or image_bytes):
        detail = " ".join(warnings)
        raise InputError(
            "Nothing to analyze. Add a screenshot, paste some text, or give a valid issue URL."
            + (f" {detail}" if detail else "")
        )

    plan = main_backend.generate(
        prompt=build_user_prompt(text, issue_data),
        system_instruction=SYSTEM_INSTRUCTION,
        image_bytes=image_bytes,
        image_mime=image_mime,
    )

    git_commands = extract_section(plan, "Git Commands")
    safety = None
    if safety_backend is None:
        warnings.append("Safety check skipped: set GEMINI_API_KEY to enable the Gemini reviewer.")
    elif not git_commands:
        warnings.append("Safety check skipped: no Git Commands section was found in the plan.")
    else:
        try:
            safety = safety_backend.generate(
                prompt=build_safety_prompt(git_commands),
                system_instruction=SAFETY_SYSTEM_INSTRUCTION,
            )
        except BackendError as exc:
            warnings.append(f"Safety check failed: {exc}")

    return PlanResult(plan=plan, git_commands=git_commands, safety=safety, warnings=warnings)
