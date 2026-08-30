"""Thin wrapper around the Gemini API so the rest of the app never talks to the SDK directly.

Centralizing this is what makes cost/latency tracking (used by the eval harness and the
observability dashboard) possible without threading instrumentation through every call site.
"""
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from app.core.config import get_settings

settings = get_settings()

# Rough public per-1M-token pricing for gemini-2.0-flash as of the model's release.
# These are placeholders — swap in the current rate card before you publish real cost numbers.
_PRICE_PER_1M_INPUT_USD = 0.10
_PRICE_PER_1M_OUTPUT_USD = 0.40
_PRICE_PER_1M_EMBED_USD = 0.00  # embeddings are free/near-free on most current tiers


def _client() -> genai.Client:
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env and add your key."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def _retry_delay_seconds(e: ClientError, default: float) -> float:
    """Extracts Google's suggested RetryInfo.retryDelay (e.g. "48s") from a 429, if present."""
    try:
        for d in e.details.get("error", {}).get("details", []):
            if d.get("@type", "").endswith("RetryInfo"):
                return float(d["retryDelay"].rstrip("s")) + 1  # small buffer
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return default


def _with_retry(fn, attempts: int = 8, delay_seconds: float = 15.0):
    """Retries a Gemini call on 429 (rate limit), honoring the server's suggested delay.

    The free tier's per-minute quota is tight enough that any multi-call flow (the agent
    loop, an eval run scoring several examples, a large ingestion batch) can trip it under
    normal use, not just heavy testing — so every call site needs this, not just embeddings.
    A fixed short backoff isn't enough for a long ingestion job hammering the same minute
    window repeatedly; honor whatever delay Google actually tells us to wait.
    """
    for attempt in range(attempts):
        try:
            return fn()
        except ClientError as e:
            if e.code == 429 and attempt < attempts - 1:
                time.sleep(_retry_delay_seconds(e, delay_seconds))
                continue
            raise


@dataclass
class GenerationResult:
    text: str
    tool_calls: list[dict] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    raw: object = None


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns a list of embedding vectors in the same order."""
    if not texts:
        return []
    client = _client()
    result = _with_retry(lambda: client.models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim),
    ))
    return [e.values for e in result.embeddings]


def generate_with_tools(
    system_instruction: str,
    contents: list[types.Content],
    tools: list[types.Tool] | None = None,
) -> GenerationResult:
    """Single-turn call to Gemini, optionally with function-calling tools declared.

    Returns text and/or tool_calls (the caller's agent loop decides what to do with them).
    """
    client = _client()
    start = time.perf_counter()

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
    )

    response = _with_retry(lambda: client.models.generate_content(
        model=settings.agent_model,
        contents=contents,
        config=config,
    ))

    latency_ms = (time.perf_counter() - start) * 1000

    tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
    tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
    cost_usd = (
        tokens_in / 1_000_000 * _PRICE_PER_1M_INPUT_USD
        + tokens_out / 1_000_000 * _PRICE_PER_1M_OUTPUT_USD
    )

    text_parts: list[str] = []
    tool_calls: list[dict] = []

    candidate = response.candidates[0] if response.candidates else None
    if candidate and candidate.content and candidate.content.parts:
        for part in candidate.content.parts:
            if getattr(part, "text", None):
                text_parts.append(part.text)
            fn_call = getattr(part, "function_call", None)
            if fn_call:
                tool_calls.append({"name": fn_call.name, "args": dict(fn_call.args or {})})

    return GenerationResult(
        text="".join(text_parts),
        tool_calls=tool_calls,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        raw=response,
    )


def judge_answer(question: str, reference_answer: str, candidate_answer: str) -> float:
    """LLM-as-judge: score a candidate answer 0-5 against a reference answer.

    Used only by the eval harness, never in the live query path.
    """
    client = _client()
    prompt = f"""You are grading an AI coding assistant's answer for correctness and completeness.

Question: {question}

Reference answer (ground truth): {reference_answer}

Candidate answer to grade: {candidate_answer}

Score the candidate answer from 0 to 5:
0 = completely wrong or irrelevant
1 = mostly wrong, touches the right area
2 = partially correct, missing key points or has errors
3 = mostly correct, minor omissions
4 = correct and complete
5 = correct, complete, and clearly explained

Respond with ONLY the integer score, nothing else."""

    response = _with_retry(lambda: client.models.generate_content(model=settings.agent_model, contents=prompt))
    text = (response.text or "0").strip()
    try:
        score = float("".join(c for c in text if c.isdigit() or c == "."))
        return max(0.0, min(5.0, score))
    except ValueError:
        return 0.0
