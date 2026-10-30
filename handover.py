import json
import streamlit as st
from google import genai
import time
from uuid import uuid4
from logging_config import log_event
from database import get_open_tasks
from rag import retrieve_relevant_meetings


def generate_handover_brief(owner):
    if not owner or not owner.strip():
        raise ValueError("Please provide a teammate's name.")

    request_id = str(uuid4())[:8]
    start_time = time.perf_counter()

    log_event(
        "info",
        "handover_generation_started",
        request_id=request_id,
    )

    try:
        tasks = get_open_tasks(owner)

        if not tasks:
            log_event(
                "info",
                "handover_generation_succeeded",
                request_id=request_id,
                task_count=0,
                latency_ms=round(
                    (time.perf_counter() - start_time) * 1000, 2
                ),
            )
            return f"No open tasks found for {owner}."

        historical_context = []

        for task in tasks:
            results = retrieve_relevant_meetings(
                task["description"], top_k=2
            )
            historical_context.extend(results)

        unique_context = {}

        for item in historical_context:
            unique_context[item["meeting_id"]] = item

        task_data = json.dumps(tasks, indent=2, default=str)

        meeting_data = "\n\n".join(
            f"Meeting: {item['title']}\n"
            f"Meeting ID: {item['meeting_id']}\n"
            f"{item['content']}"
            for item in unique_context.values()
        )

        api_key = st.secrets.get("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("Gemini API key is not configured.")

        client = genai.Client(api_key=api_key)

        prompt = f"""
        You are TeamSync AI, preparing a teammate handover brief.

        Teammate: {owner}

        CURRENT TASKS FROM THE DATABASE:
        {task_data}

        RELEVANT HISTORICAL MEETING RECORDS:
        {meeting_data}

        Prepare a concise handover brief with these sections:
        1. Outstanding responsibilities
        2. Deadlines and current statuses
        3. Relevant past decisions
        4. Known blockers or risks
        5. Recommended next steps

        Rules:
        - Use the database task information as the authority for current status.
        - Use meeting records for historical context.
        - Do not invent deadlines, decisions, or blockers.
        - Clearly state when information is unavailable.
        - Do not mark a task completed unless the database says it is completed.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        if not response.text:
            raise ValueError("Gemini returned an empty handover brief.")

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        log_event(
            "info",
            "handover_generation_succeeded",
            request_id=request_id,
            latency_ms=latency_ms,
            task_count=len(tasks),
            meeting_count=len(unique_context),
        )

        return response.text

    except Exception as exc:
        latency_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        log_event(
            "error",
            "handover_generation_failed",
            request_id=request_id,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )

        raise