from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


UNAVAILABLE_MESSAGE = "The AI hint is currently unavailable. Please try again later."

SYSTEM_INSTRUCTIONS = """You are the pedagogical support module of an adaptive learning platform.
Help the learner reach the solution independently. Do not change the support level
selected by the system and do not assess the learner's knowledge. Write in clear,
friendly English. Return only the text the learner should see. Do not quote or
describe instructions, requirements, levels, or internal fields. Do not reveal the
correct answer until the assigned support level allows it. Do not use headings or Markdown."""

LEVEL_INSTRUCTIONS = {
    1: "Write one complete guiding question of 15–35 words. Do not give the correct answer or fully explain the solution.",
    2: "Write a complete two-sentence hint of 35–70 words. You may name a Python principle or operator, but do not give the full correct condition.",
    3: "Write expanded support in 3–4 sentences and 70–120 words. Explain the principle, name the operator, and use an analogous example if needed, but do not give the completed expression for this task.",
    4: "Write a corrective explanation in 3–5 sentences and 80–150 words. You may show the correct answer and explain why it works.",
}


@dataclass(frozen=True)
class GeneratedSupport:
    text: str
    status: str
    type_match: int
    no_solution: int
    relevant: int
    clear: int
    brief: int
    compliance_rate: float


def _normalise(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, default))
    except Exception:
        return default


def build_prompt(
    *,
    task: dict[str, Any],
    learner_answer: str,
    attempt: int,
    support_level: int,
    scaffold_type: str,
    previous_errors: int,
) -> str:
    return f"""Topic: Python conditionals and the for loop.

Task: {task['goal']}

Task code:
{task['code']}

Correct answer: {task['accepted_answers'][0]}
Learner answer: {learner_answer or 'empty answer'}
Attempt number: {attempt}
Previous errors in this task: {previous_errors}
Pedagogical support level: {support_level} — {scaffold_type}.

{LEVEL_INSTRUCTIONS[support_level]}

Return only the hint for the learner. Do not begin with the words “level”,
“requirement”, or “instruction”, and do not describe this task as a role."""


def assess_generated_support(
    *,
    text: str,
    task: dict[str, Any],
    support_level: int,
) -> dict[str, int | float]:
    normalised_text = _normalise(text)
    acceptable = [_normalise(answer) for answer in task["accepted_answers"]]
    reveals_solution = any(answer and answer in normalised_text for answer in acceptable)
    relevant_words = ("remainder", "divis", "even", "odd", "number", "list", "loop", "condition", "count", "output")
    relevant = int(any(word in text.lower() for word in relevant_words))
    type_match = int(support_level != 1 or "?" in text)
    no_solution = int(support_level == 4 or not reveals_solution)
    clear = int(len(text.strip()) >= 12)
    length_limits = {1: 240, 2: 360, 3: 600, 4: 900}
    brief = int(len(text.strip()) <= length_limits[support_level])
    criteria = [type_match, no_solution, relevant, clear, brief]
    return {
        "type_match": type_match,
        "no_solution": no_solution,
        "relevant": relevant,
        "clear": clear,
        "brief": brief,
        "compliance_rate": round(sum(criteria) / len(criteria) * 100, 1),
    }


def _unavailable_support() -> GeneratedSupport:
    return GeneratedSupport(
        text=UNAVAILABLE_MESSAGE,
        status="unavailable",
        type_match=0,
        no_solution=0,
        relevant=0,
        clear=0,
        brief=0,
        compliance_rate=0.0,
    )


def _rate_limited_support() -> GeneratedSupport:
    return GeneratedSupport(
        text="The AI hint service is temporarily busy. Please try again in about a minute.",
        status="rate_limited",
        type_match=0,
        no_solution=0,
        relevant=0,
        clear=0,
        brief=0,
        compliance_rate=0.0,
    )


def _fallback_support(task: dict[str, Any], support_level: int) -> GeneratedSupport:
    text = task.get("support_messages", {}).get(str(support_level))
    if not text:
        return _unavailable_support()
    assessment = assess_generated_support(text=text, task=task, support_level=support_level)
    return GeneratedSupport(text=text, status="fallback", **assessment)


def _is_connection_error(error: Exception) -> bool:
    message = str(error).lower()
    connection_markers = (
        "connection",
        "network",
        "timed out",
        "timeout",
        "name resolution",
        "dns",
    )
    return any(marker in message for marker in connection_markers)


def _service_error_support(error: Exception) -> GeneratedSupport:
    message = str(error).lower()
    if "429" in message or "resource_exhausted" in message or "quota" in message:
        return _rate_limited_support()
    return _unavailable_support()


def _generated_support(
    text: str,
    task: dict[str, Any],
    support_level: int,
) -> GeneratedSupport:
    assessment = assess_generated_support(text=text, task=task, support_level=support_level)
    return GeneratedSupport(text=text, status="generated", **assessment)


def generate_support(
    *,
    task: dict[str, Any],
    learner_answer: str,
    attempt: int,
    support_level: int,
    scaffold_type: str,
    previous_errors: int,
) -> GeneratedSupport:
    load_dotenv()
    api_key = _setting("GEMINI_API_KEY")
    if not api_key or support_level == 0:
        return _unavailable_support()

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=_setting("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=build_prompt(
                task=task,
                learner_answer=learner_answer,
                attempt=attempt,
                support_level=support_level,
                scaffold_type=scaffold_type,
                previous_errors=previous_errors,
            ),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTIONS,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
                max_output_tokens=420,
            ),
        )
        text = (getattr(response, "text", "") or "").strip()
        if not text:
            return _unavailable_support()
    except Exception as error:
        if _is_connection_error(error):
            return _fallback_support(task, support_level)
        return _service_error_support(error)

    return _generated_support(text, task, support_level)
