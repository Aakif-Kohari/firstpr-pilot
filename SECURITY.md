# Security Policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's **Report a vulnerability** option under the repository's Security tab, or contact the maintainer through the email on their GitHub profile.

## Secrets

FirstPR Pilot reads `GEMINI_API_KEY` (and optionally `GITHUB_TOKEN`) from the environment or the sidebar. Keys are never written to disk by the app. Keep your `.env` file out of version control; it is already in `.gitignore`.

## Data handling

Screenshots, pasted text, and issue content are sent to the Gemini API when the `gemini` backend is used. Use the `ollama` backend to keep the main analysis on your machine. Do not upload screenshots containing secrets or private data.
