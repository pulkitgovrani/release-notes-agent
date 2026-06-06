"""LLM provider abstraction: Anthropic API or local Ollama (free, offline).

Both return a validated Pydantic instance from a JSON-schema-constrained call.
Pick the provider via LLM_PROVIDER env (or --provider / --local on the CLI):
  anthropic  -> Claude API   (needs ANTHROPIC_API_KEY)
  ollama     -> local model  (needs Ollama running + the model pulled)
"""
from __future__ import annotations

import os
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "anthropic").lower()


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "gemma3n:e4b")


def provider_label() -> str:
    return f"ollama:{_ollama_model()}" if _provider() == "ollama" else "anthropic"


def structured(system: str, user: str, schema: Type[T], *,
               anthropic_model: str, max_tokens: int = 8000) -> Optional[T]:
    """Run one schema-constrained completion and return the parsed model (or None)."""
    if _provider() == "ollama":
        return _ollama(system, user, schema, max_tokens)
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
