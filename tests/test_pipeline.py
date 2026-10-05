import pytest

from firstpr_pilot.backends import Backend, BackendError
from firstpr_pilot.github_issue import GitHubError
from firstpr_pilot.pipeline import InputError, build_plan

PLAN = "## Plain-English Explanation\nok\n## Git Commands\n```\ngit switch -c fix\n```\n## Draft Commit Message\nfix: x\n"


class FakeBackend(Backend):
    def __init__(self, reply=PLAN, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def generate(self, prompt, system_instruction, image_bytes=None, image_mime=None):
        self.calls.append(
            {"prompt": prompt, "system": system_instruction, "image": image_bytes, "mime": image_mime}
        )
        if self.error:
            raise self.error
        return self.reply


def test_happy_path_runs_safety_on_git_commands():
    main, safety = FakeBackend(), FakeBackend("✅ ok")
    result = build_plan(main, safety, text="boom")
    assert result.plan == PLAN and result.safety == "✅ ok"
    assert "git switch -c fix" in result.git_commands
    assert "git switch -c fix" in safety.calls[0]["prompt"]
    assert result.warnings == []


def test_image_is_forwarded():
    main = FakeBackend()
    build_plan(main, None, image_bytes=b"\x89PNG", image_mime="image/png")
    assert main.calls[0]["image"] == b"\x89PNG" and main.calls[0]["mime"] == "image/png"


def test_no_input_raises():
    with pytest.raises(InputError):
        build_plan(FakeBackend(), None, text="  ", issue_url="")


def test_bad_image_type_and_size():
    with pytest.raises(InputError):
        build_plan(FakeBackend(), None, image_bytes=b"x", image_mime="application/pdf")
    with pytest.raises(InputError):
        build_plan(FakeBackend(), None, image_bytes=b"x" * (10 * 1024 * 1024 + 1), image_mime="image/png")


def test_invalid_issue_url_warns_but_continues_with_text():
    result = build_plan(FakeBackend(), None, text="logs", issue_url="https://example.com")
    assert any("does not look like" in w for w in result.warnings)


def test_issue_fetch_failure_warns():
    def boom(*args):
        raise GitHubError("rate limited")

    result = build_plan(FakeBackend(), None, text="logs", issue_url="https://github.com/o/r/issues/1", fetch_issue=boom)
    assert any("rate limited" in w for w in result.warnings)


def test_issue_only_input_uses_fetched_data():
    main = FakeBackend()
    fake = lambda owner, repo, n: {"title": "Bug title", "body": "Body"}
    build_plan(main, None, issue_url="https://github.com/o/r/issues/9", fetch_issue=fake)
    assert "Bug title" in main.calls[0]["prompt"]


def test_only_invalid_url_raises_with_hint():
    with pytest.raises(InputError, match="does not look like"):
        build_plan(FakeBackend(), None, issue_url="https://example.com")


def test_safety_skipped_without_backend():
    result = build_plan(FakeBackend(), None, text="x")
    assert result.safety is None and any("Safety check skipped" in w for w in result.warnings)


def test_safety_failure_does_not_lose_plan():
    result = build_plan(FakeBackend(), FakeBackend(error=BackendError("quota")), text="x")
    assert result.plan == PLAN and any("quota" in w for w in result.warnings)


def test_main_backend_error_propagates():
    with pytest.raises(BackendError):
        build_plan(FakeBackend(error=BackendError("down")), None, text="x")


def test_no_git_section_skips_safety():
    safety = FakeBackend()
    result = build_plan(FakeBackend("just prose"), safety, text="x")
    assert safety.calls == [] and any("no Git Commands" in w for w in result.warnings)
