from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from adaptive_engine import determine_support
from analytics import calculate_metrics, session_dataframe
from diagnostic_engine import diagnose_attempt
from llm_service import generate_support
from logger import append_interaction


ROOT = Path(__file__).parent
TASKS_PATH = ROOT / "data" / "tasks.json"
LOG_PATH = ROOT / "results" / "experiment_log.csv"


def load_tasks() -> list[dict]:
    with TASKS_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def initialise_state() -> None:
    defaults = {
        "session_id": str(uuid.uuid4()),
        "task_index": 0,
        "support_level": 0,
        "events": [],
        "task_started_at": time.monotonic(),
        "task_solved": False,
        "last_feedback": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_session() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialise_state()


def move_to_next_task() -> None:
    st.session_state.task_index += 1
    st.session_state.task_started_at = time.monotonic()
    st.session_state.task_solved = False
    st.session_state.last_feedback = None


def submit_answer(task: dict, answer: str) -> None:
    task_events = [event for event in st.session_state.events if event["task_id"] == task["id"]]
    attempt = len(task_events) + 1
    diagnosis = diagnose_attempt(
        answer=answer,
        task=task,
        attempt=attempt,
        task_events=task_events,
        session_events=st.session_state.events,
    )
    decision = determine_support(
        correct=diagnosis.correct,
        attempt=attempt,
        previous_support=st.session_state.support_level,
        task_support_cap=task.get("support_cap", 4),
    )

    if diagnosis.correct:
        ai_response = ""
        ai_status = "not_needed"
        ai_checks = {
            "type_match": "",
            "no_solution": "",
            "relevant": "",
            "clear": "",
            "brief": "",
            "compliance_rate": "",
        }
    else:
        generated = generate_support(
            task=task,
            learner_answer=answer.strip(),
            attempt=attempt,
            support_level=decision.support_after,
            scaffold_type=decision.scaffold_type,
            previous_errors=diagnosis.previous_errors,
        )
        ai_response = generated.text
        ai_status = generated.status
        ai_checks = {
            "type_match": generated.type_match,
            "no_solution": generated.no_solution,
            "relevant": generated.relevant,
            "clear": generated.clear,
            "brief": generated.brief,
            "compliance_rate": generated.compliance_rate,
        }

    record = {
        "session_id": st.session_state.session_id,
        "task_id": task["id"],
        "attempt": attempt,
        "user_answer": answer.strip(),
        "correct": diagnosis.correct,
        "previous_errors": diagnosis.previous_errors,
        "previous_hints": diagnosis.previous_hints,
        "previous_results": "|".join("1" if result else "0" for result in diagnosis.previous_results),
        "support_level": decision.support_after,
        "previous_support_level": decision.support_before,
        "support_direction": decision.direction,
        "scaffold_type": decision.scaffold_type,
        "ai_response": ai_response,
        "ai_status": ai_status,
        "ai_type_match": ai_checks["type_match"],
        "ai_no_solution": ai_checks["no_solution"],
        "ai_relevant": ai_checks["relevant"],
        "ai_clear": ai_checks["clear"],
        "ai_brief": ai_checks["brief"],
        "ai_compliance_rate": ai_checks["compliance_rate"],
        "response_time_sec": round(time.monotonic() - st.session_state.task_started_at, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    st.session_state.events.append(record)
    append_interaction(record, LOG_PATH)
    st.session_state.support_level = decision.support_after

    if diagnosis.correct:
        st.session_state.task_solved = True
        st.session_state.last_feedback = {"kind": "success", "text": "Correct! Great work."}
    else:
        st.session_state.last_feedback = {
            "kind": "hint" if ai_status in {"generated", "fallback"} else "unavailable",
            "text": ai_response,
        }


def render_learning_tab(tasks: list[dict]) -> None:
    if st.session_state.task_index >= len(tasks):
        st.success("You have completed all tasks. Review your progress in the next tab.")
        if st.button("Start again", type="primary"):
            reset_session()
            st.rerun()
        return

    task = tasks[st.session_state.task_index]
    completed = st.session_state.task_index
    next_attempt = len([event for event in st.session_state.events if event["task_id"] == task["id"]]) + 1
    st.progress(completed / len(tasks), text=f"Task {completed + 1} of {len(tasks)}")
    st.subheader(f"Task {task['id']}. {task['title']}")
    st.write(task["goal"])
    st.code(task["code"], language="python")
    st.caption(f"Attempt {next_attempt}. Support level: {st.session_state.support_level} of 4")

    if task["id"] == 3:
        st.caption("Try to solve this task independently before using hints.")

    feedback = st.session_state.last_feedback
    if feedback:
        if feedback["kind"] == "success":
            st.success(feedback["text"])
        elif feedback["kind"] == "hint":
            st.warning("Not quite. Try again.")
            st.info(f"Hint\n\n{feedback['text']}")
        else:
            st.warning("Not quite. Try again.")
            st.error(feedback["text"])

    if not st.session_state.task_solved:
        input_label = "Enter the Python condition:" if task["answer_kind"] == "expression" else "Enter the number:"
        placeholder = "For example: n % 2 == 0" if task["answer_kind"] == "expression" else "For example: 3"
        with st.form(f"answer_form_{task['id']}", clear_on_submit=True):
            answer = st.text_input(input_label, placeholder=placeholder)
            submitted = st.form_submit_button("Check answer", type="primary")
        if submitted:
            with st.spinner("Checking your answer…"):
                submit_answer(task, answer)
            st.rerun()
    else:
        label = "Finish" if task["id"] == len(tasks) else "Next task"
        if st.button(label, type="primary"):
            move_to_next_task()
            st.rerun()


def render_progress_tab(tasks: list[dict]) -> None:
    st.subheader("Your progress")
    records = st.session_state.events
    metrics = calculate_metrics(records, st.session_state.support_level)

    row1 = st.columns(4)
    row1[0].metric("Tasks completed", f"{metrics['completed_tasks']} / {len(tasks)}")
    row1[1].metric("Attempts", metrics["attempts"])
    row1[2].metric("Incorrect answers", metrics["errors"])
    row1[3].metric("Correct answers", f"{metrics['correct_rate']}%")

    row2 = st.columns(4)
    row2[0].metric("Correct on first attempt", metrics["first_try_correct"])
    row2[1].metric("Hints received", metrics["ai_hints"])
    row2[2].metric("Highest support level", metrics["max_support"])
    row2[3].metric("Current support level", metrics["current_support"])

    frame = session_dataframe(records)
    if frame.empty:
        st.info("Your results will appear here after the first attempt.")
        return

    st.markdown("#### Support during practice")
    figure, axis = plt.subplots(figsize=(8, 3.2))
    steps = range(1, len(frame) + 1)
    axis.plot(steps, frame["support_level"].astype(int), marker="o", color="#4169E1")
    axis.set_ylim(0, 4)
    axis.set_xticks(list(steps))
    axis.set_xlabel("Attempt")
    axis.set_ylabel("Support level")
    axis.grid(axis="y", alpha=0.25)
    st.pyplot(figure, clear_figure=True)

    st.markdown("#### Your attempts")
    visible = frame.rename(
        columns={
            "task_id": "Task",
            "attempt": "Attempt",
            "user_answer": "Your answer",
            "correct": "Result",
            "support_level": "Support level",
            "response_time_sec": "Time, s",
        }
    )
    visible["Result"] = visible["Result"].map({True: "correct", False: "try again"})
    st.dataframe(
        visible[["Task", "Attempt", "Your answer", "Result", "Support level", "Time, s"]],
        hide_index=True,
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title="Python Practice", page_icon="🐍", layout="wide")
    initialise_state()
    tasks = load_tasks()

    st.title("Python Practice: Conditionals and the `for` Loop")
    st.caption("Complete the tasks in order. You will receive a hint when needed.")

    with st.sidebar:
        st.header("Your progress")
        st.metric("Task", f"{min(st.session_state.task_index + 1, len(tasks))} / {len(tasks)}")
        st.metric("Support level", f"{st.session_state.support_level} of 4")
        if st.button("Start again"):
            reset_session()
            st.rerun()

    learning_tab, progress_tab = st.tabs(["Tasks", "My progress"])
    with learning_tab:
        render_learning_tab(tasks)
    with progress_tab:
        render_progress_tab(tasks)


if __name__ == "__main__":
    main()
