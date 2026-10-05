"""FirstPR Pilot: Streamlit UI."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from firstpr_pilot.backends import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMMA_MODEL,
    DEFAULT_OLLAMA_MODEL,
    Backend,
    BackendError,
    GeminiBackend,
    OllamaBackend,
)
from firstpr_pilot.pipeline import InputError, build_plan

load_dotenv()


def make_backends(
    choice: str, api_key: str, gemma_model: str, gemini_model: str, ollama_model: str
) -> tuple[Backend, Backend | None]:
    """Return (main_backend, safety_backend). The safety backend is None without an API key."""
    safety: Backend | None = (
        GeminiBackend(gemini_model, api_key=api_key) if api_key else None
    )
    if choice == "ollama":
        return OllamaBackend(ollama_model), safety
    if safety is None:
        raise BackendError("GEMINI_API_KEY is not set. Add it in the sidebar or your .env file.")
    return GeminiBackend(gemma_model, api_key=api_key), safety


def main() -> None:
    st.set_page_config(page_title="FirstPR Pilot", page_icon="🚀", layout="wide")
    st.title("🚀 FirstPR Pilot")
    st.caption(
        "An AI mentor for your first open-source contribution. "
        "Powered by open-weight Gemma 4 and the Gemini API."
    )

    with st.sidebar:
        st.header("Settings")
        env_backend = os.getenv("BACKEND", "gemini").lower()
        choice = st.selectbox(
            "Main model backend",
            ["gemini", "ollama"],
            index=1 if env_backend == "ollama" else 0,
            help="'gemini' runs Gemma 4 through the Gemini API. 'ollama' runs Gemma locally.",
        )
        api_key = st.text_input(
            "Gemini API key",
            type="password",
            value=os.getenv("GEMINI_API_KEY", ""),
            help="Used for Gemma 4 (gemini backend) and the Gemini safety reviewer. Never stored.",
        )
        gemma_model = st.text_input("Gemma model", os.getenv("GEMMA_MODEL", DEFAULT_GEMMA_MODEL))
        gemini_model = st.text_input(
            "Gemini model (safety review)", os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        )
        ollama_model = st.text_input(
            "Ollama model", os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        )

    st.subheader("1. Give it some context")
    uploaded = st.file_uploader("Screenshot of an error or UI bug", type=["png", "jpg", "jpeg", "webp"])
    text = st.text_area("Paste error logs or describe the bug", height=140)
    issue_url = st.text_input(
        "Public GitHub issue URL (optional)", placeholder="https://github.com/owner/repo/issues/123"
    )

    if st.button("Analyze and generate plan", type="primary"):
        try:
            main_backend, safety_backend = make_backends(
                choice, api_key, gemma_model, gemini_model, ollama_model
            )
            with st.spinner("Building your contribution plan..."):
                result = build_plan(
                    main_backend,
                    safety_backend,
                    text=text,
                    issue_url=issue_url,
                    image_bytes=uploaded.getvalue() if uploaded else None,
                    image_mime=uploaded.type if uploaded else None,
                )
        except (InputError, BackendError) as exc:
            st.error(str(exc))
            return

        for warning in result.warnings:
            st.warning(warning)

        st.subheader("2. Your contribution plan")
        st.markdown(result.plan)

        if result.safety:
            with st.expander("🛡️ Git safety check (second opinion from Gemini)", expanded=True):
                st.markdown(result.safety)


if __name__ == "__main__":
    main()
