"""Grounded LLM explanation layer for deterministic investigations.

This module deliberately has no database imports: its only factual input is the
already-computed investigation result supplied by the caller.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.config import get_llm_config
from app.schemas import AIExplanation, InvestigationResult


class LLMConfigurationError(RuntimeError):
    """The explanation provider has not been configured."""


class LLMProviderError(RuntimeError):
    """The explanation provider returned an unusable response or failed."""


class LLMTimeoutError(LLMProviderError):
    """The provider request timed out."""


SYSTEM_PROMPT = """You explain payment settlement investigations to a support agent.
The supplied JSON is the output of a deterministic reconciliation engine and is
the only source of truth. Do not query for, infer, or invent records, statuses,
amounts, timestamps, settlement IDs, or reasons not explicitly present in it.
Do not override its root_cause, settlement_status, recommended_action, or
confidence. If the result is insufficient_evidence or conflicting_evidence, say
what is missing or conflicting and what cannot be determined; never propose an
unsupported cause. Distinguish facts from likely explanations and reflect the
given confidence without calculating a new score. Be concise and professional.
Return only JSON matching the requested schema, with support-friendly text in
summary, what_happened, why, evidence, recommended_action, and uncertainty.
"""

EXPLANATION_SCHEMA: dict[str, Any] = {
    "name": "settlement_explanation",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "what_happened": {"type": "string"},
            "why": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "recommended_action": {"type": "string"},
            "uncertainty": {"type": "string"},
        },
        "required": ["summary", "what_happened", "why", "evidence", "recommended_action", "uncertainty"],
    },
}


def _get_client(api_key: str, base_url: str | None) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMConfigurationError("OpenAI-compatible client dependency is not installed") from exc
    return OpenAI(api_key=api_key, base_url=base_url, timeout=20.0, max_retries=0)


def generate_explanation(investigation_result: Mapping[str, Any]) -> dict[str, Any]:
    """Explain one deterministic result; never access storage or reconcile data."""
    validated_result = InvestigationResult.model_validate(dict(investigation_result))
    api_key, model, base_url = get_llm_config()
    if not api_key:
        raise LLMConfigurationError("LLM_API_KEY is not configured")

    client = _get_client(api_key, base_url)
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(validated_result.model_dump(), default=str)},
            ],
            response_format={"type": "json_schema", "json_schema": EXPLANATION_SCHEMA},
            temperature=0,
        )
        content = completion.choices[0].message.content
        if not content:
            raise LLMProviderError("Provider returned no explanation")
        generated = AIExplanation.model_validate_json(content)
        # Evidence and next action are displayed verbatim from the deterministic
        # result so the model cannot add unsupported evidence or alter the action.
        return generated.model_copy(
            update={
                "evidence": list(validated_result.evidence),
                "recommended_action": validated_result.recommended_action,
            }
        ).model_dump()
    except LLMProviderError:
        raise
    except Exception as exc:
        # Import locally so tests do not need the client package when mocking.
        try:
            from openai import APITimeoutError
        except ImportError:
            APITimeoutError = ()  # type: ignore[assignment,misc]
        if isinstance(exc, APITimeoutError):
            raise LLMTimeoutError("Provider request timed out") from exc
        raise LLMProviderError("Provider request failed") from exc
