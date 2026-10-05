# Architecture

## Goals

- Keep AI providers swappable behind one small interface.
- Keep the core flow independent of the UI so it can be tested offline.
- Fail with clear, beginner-friendly messages.

## Modules

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit UI, settings sidebar, wiring backends to the pipeline |
| `firstpr_pilot/pipeline.py` | `build_plan()`: validates input, fetches the issue, calls the main backend, extracts the Git commands, calls the safety reviewer |
| `firstpr_pilot/backends.py` | `Backend` interface; `GeminiBackend` (Gemini API, works for `gemma-4-*` and `gemini-*` IDs); `OllamaBackend` (local `/api/chat`) |
| `firstpr_pilot/github_issue.py` | Issue URL parsing and REST fetch with friendly errors |
| `firstpr_pilot/prompts.py` | System instruction, user/safety prompts, `extract_section()` for Markdown output |

## Request flow

1. The UI collects an optional screenshot, text, and issue URL.
2. `build_plan()` validates the image (PNG/JPEG/WebP, up to 10 MB) and fetches the issue, if any. A bad URL or a failed fetch becomes a warning, not a crash.
3. The main backend receives a user prompt (issue title and body plus notes, truncated to safe lengths) with the image and a structured system instruction.
4. The `## Git Commands` section is extracted with a tolerant parser (handles `##`/`###`, numbering, bold).
5. A second model (Gemini Flash) reviews those commands. Its failure never discards the plan.

## Design decisions

- **Two models, two jobs.** Gemma 4 mentors; a different model reviews. Independent review catches mistakes a single model repeats.
- **System-instruction fallback.** If a model rejects system instructions, `GeminiBackend` retries once with the instruction inlined in the prompt.
- **Optional safety backend.** Without a Gemini key the app still works (Ollama), and tells the user the review was skipped.
- **No persistence.** Nothing is stored; keys live in the environment or the session.

## Extending

Implement `Backend.generate(prompt, system_instruction, image_bytes, image_mime)` and register it in `make_backends()` in `app.py`.
