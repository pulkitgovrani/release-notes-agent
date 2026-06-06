"""LLM provider abstraction: Anthropic API, NVIDIA NIM, or local Ollama (free, offline).

All return a validated Pydantic instance from a JSON-schema-constrained call.
Pick the provider via LLM_PROVIDER env (or --provider / --local / --nvidia on the CLI):
  anthropic  -> Claude API   (needs ANTHROPIC_API_KEY)
  nvidia     -> NVIDIA NIM    (needs NVIDIA_API_KEY; OpenAI-compatible, open models)
  ollama     -> local model  (needs Ollama running + the model pulled)
"""
from __future__ import annotations

import json
import os
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "anthropic").lower()


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "gemma3n:e4b")


def _nvidia_model() -> str:
    return os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")


def provider_label() -> str:
    p = _provider()
    if p == "ollama":
        return f"ollama:{_ollama_model()}"
    if p == "nvidia":
        return f"nvidia:{_nvidia_model()}"
    return "anthropic"


def structured(system: str, user: str, schema: Type[T], *,
               anthropic_model: str, max_tokens: int = 8000) -> Optional[T]:
    """Run one schema-constrained completion and return the parsed model (or None)."""
    p = _provider()
    if p == "ollama":
        return _ollama(system, user, schema, max_tokens)
    if p == "nvidia":
        return _nvidia(system, user, schema, max_tokens)
    return _anthropic(system, user, schema, anthropic_model, max_tokens)


def _anthropic(system, user, schema, model, max_tokens):
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    return resp.parsed_output


def _nvidia(system, user, schema, max_tokens):
    """NVIDIA NIM (build.nvidia.com) — OpenAI-compatible, runs open models (Llama, Nemotron…).
    No Claude here: this uses your NVIDIA_API_KEY to call a hosted open model.
    We constrain via JSON schema in the prompt + json_object mode, then validate & retry."""
    from openai import OpenAI
    client = OpenAI(
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.getenv("NVIDIA_API_KEY"),
    )
    model = _nvidia_model()
    system = (system + "\n\nReturn ONLY a JSON object matching this JSON Schema "
              "(no prose, no markdown fences):\n" + json.dumps(schema.model_json_schema()))
    last_err = None
    for _ in range(3):  # open models sometimes need a nudge to nail the JSON
        kwargs = dict(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0,
            max_tokens=max_tokens,
        )
        try:  # json_object mode helps; some NIM models reject it, so fall back to prompt-only
            resp = client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
        except Exception:
            resp = client.chat.completions.create(**kwargs)
        content = (resp.choices[0].message.content or "").strip()
        if content.startswith("```"):  # strip stray ```json fences
            content = content.split("```")[1].removeprefix("json").strip() if "```" in content[3:] else content
        try:
            return schema.model_validate_json(content)
        except ValidationError as e:
            last_err = e
            user += "\n\nReturn ONLY valid JSON matching the schema. No prose, no markdown."
    raise RuntimeError(
        f"NVIDIA model '{model}' didn't return valid JSON after retries. "
        f"Try a larger instruct model (e.g. meta/llama-3.3-70b-instruct). Last error: {last_err}"
    )


def _ollama(system, user, schema, max_tokens):
    import ollama
    client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    model = _ollama_model()
    last_err = None
    for _ in range(2):  # small local models sometimes need a nudge to nail the JSON
        resp = client.chat(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            format=schema.model_json_schema(),       # Ollama structured outputs
            options={"temperature": 0, "num_predict": max_tokens},
        )
        content = resp["message"]["content"] if isinstance(resp, dict) else resp.message.content
        try:
            return schema.model_validate_json(content)
        except ValidationError as e:
            last_err = e
            user += "\n\nReturn ONLY valid JSON matching the schema. No prose, no markdown."
    raise RuntimeError(
        f"Ollama model '{model}' didn't return valid JSON after retries. "
        f"Try a larger model. Last error: {last_err}"
    )
