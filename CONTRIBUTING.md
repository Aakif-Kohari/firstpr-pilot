# Contributing to FirstPR Pilot

Thanks for helping! This project is built to make open source less intimidating, so first-time contributors are especially welcome.

## Set up

```bash
git clone https://github.com/<your-username>/firstpr-pilot.git
cd firstpr-pilot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

All tests must pass without an API key.

## Workflow

1. Fork the repo and create a branch: `git switch -c feat/short-description`.
2. Make your change and add or update tests in `tests/`.
3. Run `pytest`.
4. Commit using [Conventional Commits](https://www.conventionalcommits.org), e.g. `fix(backends): handle empty Ollama response`.
5. Push your branch and open a pull request describing what changed and why. Link the issue with `Closes #<number>`.

## Ideas for first contributions

- Add a "copy all commands" button to the UI
- Support more image types or multiple screenshots
- Add a backend for another OpenAI-compatible local server
- Let the user paste a repository's `CONTRIBUTING.md` so the plan follows it
- Improve error messages or add a language selector
- Add tests for edge cases in `extract_section`

## Guidelines

- Keep AI calls behind the `Backend` interface in `firstpr_pilot/backends.py`.
- Keep UI code in `app.py`; put logic in `firstpr_pilot/` so it stays testable.
- Never commit API keys or a `.env` file.
- Be kind. Everyone here is learning.
