"""The agent's multi-step reasoning loop.

Each iteration: ask Gemini (with tool declarations) what to do next. If it returns a function
call, execute the tool, feed the result back as a new turn, and loop. If it returns text, that's
the final answer. Capped at AGENT_MAX_STEPS to bound cost and latency — an agent that never
stops calling tools is a production incident, not a feature.

This module is a generator (`run_agent`) so the API layer can stream each step over SSE.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Generator
from uuid import UUID

from google.genai import types
from sqlalchemy.orm import Session

from app.agent.tools import (
    TOOL_DECLARATIONS,
    tool_git_blame,
    tool_grep,
    tool_read_file,
    tool_run_tests,
    tool_search_code,
)
from app.core.config import get_settings
from app.core.llm import generate_with_tools

settings = get_settings()

SYSTEM_INSTRUCTION = """You are RepoPilot, an AI assistant that answers questions about a \
specific codebase. You have tools to search the code, read files, grep for exact matches, run \
the test suite, and check git blame. Always ground your answer in what the tools return — do \
not guess at code you have not looked at. Cite file paths and line numbers in your final answer. \
When you have enough information, respond with plain text (no further tool call) as your final \
answer."""


@dataclass
class AgentStep:
    step_index: int
    step_type: str  # "tool_call" | "final_answer"
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: str | None = None
    text: str | None = None
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


@dataclass
class AgentRunResult:
    final_answer: str
    steps: list[AgentStep] = field(default_factory=list)
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0


def _execute_tool(db: Session, project_id: UUID, repo_root: str, name: str, args: dict) -> str:
    if name == "search_code":
        return tool_search_code(db, project_id, args.get("query", ""))
    if name == "read_file":
        return tool_read_file(repo_root, args.get("file_path", ""), args.get("start_line"), args.get("end_line"))
    if name == "grep":
        return tool_grep(repo_root, args.get("pattern", ""))
    if name == "run_tests":
        return tool_run_tests(repo_root, args.get("test_path", ""))
    if name == "git_blame":
        return tool_git_blame(repo_root, args.get("file_path", ""), args.get("start_line", 0), args.get("end_line", 0))
    return f"Unknown tool: {name}"


def run_agent(
    db: Session, project_id: UUID, repo_root: str, question: str
) -> Generator[AgentStep, None, AgentRunResult]:
    """Runs the agent loop, yielding an AgentStep after every model call / tool execution.

    Usage:
        gen = run_agent(...)
        for step in gen:
            ... stream step to client ...
        result = gen.value  # after StopIteration, via `return`
    """
    contents: list[types.Content] = [types.Content(role="user", parts=[types.Part(text=question)])]

    steps: list[AgentStep] = []
    total_latency = 0.0
    total_cost = 0.0
    start_time = time.perf_counter()

    for step_index in range(settings.agent_max_steps):
        result = generate_with_tools(SYSTEM_INSTRUCTION, contents, tools=TOOL_DECLARATIONS)
        total_latency += result.latency_ms
        total_cost += result.cost_usd

        if result.tool_calls:
            call = result.tool_calls[0]  # execute one tool call per step, sequential reasoning
            tool_output = _execute_tool(db, project_id, repo_root, call["name"], call["args"])

            step = AgentStep(
                step_index=step_index,
                step_type="tool_call",
                tool_name=call["name"],
                tool_input=call["args"],
                tool_output=tool_output,
                latency_ms=result.latency_ms,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost_usd=result.cost_usd,
            )
            steps.append(step)
            yield step

            # Feed the model's function call + our tool result back into the conversation.
            contents.append(types.Content(
                role="model",
                parts=[types.Part(function_call=types.FunctionCall(name=call["name"], args=call["args"]))],
            ))
            contents.append(types.Content(
                role="user",
                parts=[types.Part(function_response=types.FunctionResponse(
                    name=call["name"], response={"result": tool_output}
                ))],
            ))
            continue

        # No tool call -> this is the final answer.
        step = AgentStep(
            step_index=step_index,
            step_type="final_answer",
            text=result.text,
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
        )
        steps.append(step)
        yield step

        total_wall_ms = (time.perf_counter() - start_time) * 1000
        return AgentRunResult(
            final_answer=result.text,
            steps=steps,
            total_latency_ms=total_wall_ms,
            total_cost_usd=total_cost,
        )

    # Hit max steps without a final answer — degrade gracefully instead of erroring.
    fallback_text = (
        "I wasn't able to reach a confident answer within the step budget. "
        "Here's what I found so far:\n\n" + "\n".join(
            f"- {s.tool_name}: {s.tool_output[:200]}..." for s in steps if s.step_type == "tool_call"
        )
    )
    fallback_step = AgentStep(step_index=len(steps), step_type="final_answer", text=fallback_text)
    steps.append(fallback_step)
    yield fallback_step

    total_wall_ms = (time.perf_counter() - start_time) * 1000
    return AgentRunResult(
        final_answer=fallback_text, steps=steps, total_latency_ms=total_wall_ms, total_cost_usd=total_cost
    )
