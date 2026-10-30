import time
import streamlit as st
from uuid import uuid4
from google import genai
from typing import Optional
from logging_config import log_event
from pydantic import BaseModel, Field


# 1. Define the structure of each action item
class ActionItem(BaseModel):
    description: str
    owner: Optional[str] = Field(
        default=None,
        description=(
            "The explicitly named person responsible for this action item, "
            "or null when no responsible person is identified."
        ),
    )
    due_date: Optional[str] = None


# 2. Define the complete meeting analysis structure
class MeetingAnalysis(BaseModel):
    summary: str
    decisions: list[str]
    action_items: list[ActionItem]
    risks: list[str] = Field(default_factory=list)


# 3. Connect to Gemini
def analyze_meeting(title, participants, notes):
    if not notes or not notes.strip():
        raise ValueError("Meeting notes cannot be empty.")

    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key is not configured.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an AI meeting assistant.

    Analyze the meeting information below.

    Meeting title: {title}
    Participants: {participants or "Not specified"}

    Raw meeting notes:
    {notes}

    Extract:
    1. A concise summary.
    2. Explicit decisions made during the meeting.
    3. Action items, assigning each action to the explicitly identified
       responsible person and including a due date when stated.
    4. Risks or blockers explicitly mentioned.

    Rules:
    - For each action item, extract the owner from the person explicitly
      assigned that action. Assignment wording can appear in different forms,
      for example:
        - "Sarvesh will check for bugs." -> owner: Sarvesh
        - "Assign bug checking to Sarvesh." -> owner: Sarvesh
        - "Sarvesh is responsible for testing." -> owner: Sarvesh
        - "Rahul will ensure all files are compiled and tested."
          -> owner: Rahul
    - Keep the action description focused on the work, not the person's name.
    - Use null when the notes do not explicitly identify who is responsible.
      Do not infer an owner just because a person's name appears elsewhere,
      and do not assign a group action to an individual without evidence.
    - Do not invent decisions, owners, deadlines, or risks.
    - Use null for an unknown due date.
    - Represent known due dates as YYYY-MM-DD when possible.
    - If the year is not provided, do not guess it.
    - Keep the summary faithful to the notes.
    """

    request_id = str(uuid4())[:8]
    start_time = time.perf_counter()

    log_event(
        "info",
        "ai_analysis_started",
        request_id=request_id,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": MeetingAnalysis,
            },
        )

        result = response.parsed

        if result is None:
            raise ValueError("Gemini returned no structured result.")

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        log_event(
            "info",
            "ai_analysis_succeeded",
            request_id=request_id,
            latency_ms=latency_ms,
        )

        return result

    except Exception as exc:
        latency_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        log_event(
            "error",
            "ai_analysis_failed",
            request_id=request_id,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
        raise