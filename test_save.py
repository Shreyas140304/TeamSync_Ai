import streamlit as st
from datetime import date

from ai_service import analyze_meeting
from database import init_db, save_meeting

init_db()

st.title("Test Meeting Storage")

title = st.text_input("Meeting title", "Website Launch")
participants = st.text_input("Participants", "Priya, Rahul")
notes = st.text_area(
    "Meeting notes",
    "Priya will finish the homepage by November 5. "
    "Rahul will test payments by November 7. "
    "The team decided to launch after testing is complete."
)

if st.button("Analyze and Save"):
    try:
        analysis = analyze_meeting(title, participants, notes)

        meeting_id = save_meeting(
            title=title,
            meeting_date=date.today().isoformat(),
            participants=participants,
            raw_notes=notes,
            analysis=analysis,
        )

        st.success(f"Meeting saved successfully! ID: {meeting_id}")
        st.json(analysis.model_dump())

    except Exception as exc:
        st.error(f"Operation failed: {exc}")